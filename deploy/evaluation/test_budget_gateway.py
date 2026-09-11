import concurrent.futures
import io
import json
import threading
import time
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from budget_gateway import CHAT_MODEL, EMBED_MODEL, Ledger, prepare, start_gateway


class BudgetTests(unittest.TestCase):
    def test_confirmed_closed_total_covers_uncertain_calls_without_erasing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")
            ledger.reserve("chat")
            with self.assertRaises(ValueError):
                ledger.record_upper_bound(1, 50, "user confirmed under fifty cents")
            ledger.record_upper_bound(1, 50, "user confirmed under fifty cents; run stopped",
                                      externally_confirmed_closed=True)
            self.assertEqual(ledger.summary()["attempts"], 1)
            self.assertEqual(ledger.summary()["accounted_usd"], 0.5)
            self.assertTrue(ledger.summary()["checkpoint_is_upper_bound"])
            ledger.reserve("new call")
            self.assertEqual(ledger.summary()["accounted_usd"], 0.6)

    def test_temporary_reservation_shortage_waits_for_settlement(self):
        self.test_gateway_limits_inflight_upstream_calls(19)

    def test_gateway_limits_inflight_upstream_calls(self, existing_unknown=0):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")
            server = start_gateway("not-a-key", ledger, "local")
            for _ in range(existing_unknown):
                ledger.reserve("prior uncertain call")
            if existing_unknown:
                ledger.record_upper_bound(existing_unknown, 185, "fixture closed billing bound",
                                          externally_confirmed_closed=True)
            original = urllib.request.urlopen
            active = peak = 0
            lock = threading.Lock()

            def upstream(request, *args, **kwargs):
                nonlocal active, peak
                if not request.full_url.startswith("https://openrouter.ai/"):
                    return original(request, *args, **kwargs)
                with lock:
                    active += 1
                    peak = max(peak, active)
                time.sleep(0.05)
                with lock:
                    active -= 1
                return io.BytesIO(b'{"usage":{"cost":0.0001}}')

            def call(_):
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/v1/embeddings",
                    data=json.dumps({"input": "test", "model": EMBED_MODEL}).encode(),
                    headers={"Authorization": "Bearer local"})
                with urllib.request.urlopen(request) as response:
                    return response.status

            try:
                with patch("urllib.request.urlopen", side_effect=upstream):
                    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                        self.assertEqual(list(pool.map(call, range(6))), [200] * 6)
                self.assertEqual(peak, 1 if existing_unknown else 2)
                self.assertEqual(ledger.summary()["reserved_usd"], 0)
            finally:
                server.shutdown()
                server.server_close()

    def test_upper_bound_and_reported_costs(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")
            ledger.finish(ledger.reserve("chat"), "completed")
            ledger.record_upper_bound(1, 6, "user says below six cents")
            self.assertIsNone(ledger.summary()["actual_cost_usd"])
            ledger.finish(ledger.reserve("chat"), "completed", 0.000808)
            self.assertEqual(ledger.summary()["accounted_usd"], 0.060808)
            for bad in (None, "NaN", -1, True):
                ledger.finish(ledger.reserve("chat"), "completed", bad)
            self.assertEqual(ledger.summary()["reserved_usd"], 0.4)
            with self.assertRaises(ValueError):
                ledger.record_upper_bound(1, 0, "altered")

    def test_local_lifecycle_mode_cannot_spend(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")
            server = start_gateway("not-a-key", ledger, "local", allow_requests=False)
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/v1/embeddings", data=b"{}")
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code, 403)
                self.assertEqual(ledger.summary()["attempts"], 0)
            finally:
                server.shutdown()
                server.server_close()

    def test_confirmed_cost_retains_history_and_bounds_new_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")
            for _ in range(8):
                ledger.finish(ledger.reserve("/v1/embeddings"), "completed")
            ledger.settle(8, 6, "user confirmed total")
            ledger.settle(8, 6, "user confirmed total")
            self.assertTrue(ledger.can_reserve())
            self.assertEqual(ledger.summary()["actual_cost_usd"], 0.06)
            for _ in range(19):
                ledger.reserve("/v1/embeddings")
            self.assertEqual(ledger.summary()["attempts"], 27)
            self.assertEqual(ledger.summary()["accounted_usd"], 1.96)
            self.assertFalse(ledger.can_reserve())
            with self.assertRaises(ValueError):
                ledger.reserve("/v1/embeddings")
            for args in ((8, 5, "changed"), (28, 6, "missing"), (9, 6, "unfinished"),
                         (7, 6, "older"), (8, -1, "negative")):
                with self.assertRaises(ValueError):
                    ledger.settle(*args)

    def test_budget_survives_restart_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            for _ in range(20):
                ledger = Ledger(path)
                identity = ledger.reserve("/v1/chat/completions")
                ledger.finish(identity, "failed_or_uncertain")
            with self.assertRaises(ValueError):
                Ledger(path).reserve("/v1/embeddings")
            self.assertEqual(Ledger(path).summary()["reserved_usd"], 2)

    def test_concurrent_requests_cannot_overrun(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")

            def reserve(_):
                try:
                    ledger.reserve("/v1/embeddings")
                    return True
                except ValueError:
                    return False

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(sum(pool.map(reserve, range(40))), 20)

    def test_request_cannot_override_limits_or_enable_paid_tools(self):
        payload = prepare("/v1/chat/completions", {
            "model": CHAT_MODEL, "messages": [{"role": "user", "content": "Synthetic text"}],
            "max_tokens": 1000000, "plugins": [{"id": "web"}], "stream": True,
            "provider": {"max_price": {"prompt": 999}},
        })
        self.assertEqual(payload["max_tokens"], 8192)
        self.assertFalse(payload["stream"])
        self.assertNotIn("plugins", payload)
        self.assertEqual(payload["provider"]["max_price"]["prompt"], 0.30)

    def test_wrong_model_multimedia_and_oversized_input_rejected(self):
        for model, content in (("unauthorized", "text"), (CHAT_MODEL, [{"type": "image"}]),
                               (CHAT_MODEL, "x" * 40000)):
            with self.assertRaises(ValueError):
                prepare("/v1/chat/completions", {
                    "model": model, "messages": [{"role": "user", "content": content}],
                })


if __name__ == "__main__":
    unittest.main()
