"""Conservative trial-only gateway: $0.10 reservations within a $2 total cap.

Never give Cognee the upstream key. Route its text-only requests through this
loopback gateway; every retry consumes another reservation, even on network error.
"""

import json
import sqlite3
import threading
import urllib.error
import urllib.request
from contextlib import closing
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CHAT_MODEL = "google/gemini-3.5-flash-lite"
EMBED_MODEL = "google/gemini-embedding-001"
MAX_BYTES = 32768
CAP_CENTS = 200


def prepare(path: str, payload: dict) -> dict:
    if len(json.dumps(payload).encode()) > MAX_BYTES:
        raise ValueError("trial request exceeds 32 KiB")
    if path == "/v1/chat/completions":
        if payload.get("model") != CHAT_MODEL:
            raise ValueError("model not authorized")
        messages = payload.get("messages")
        if not isinstance(messages, list) or not 1 <= len(messages) <= 20:
            raise ValueError("1 to 20 text messages required")
        if any(not isinstance(m, dict) or m.get("role") not in {"system", "user", "assistant"}
               or not isinstance(m.get("content"), str) for m in messages):
            raise ValueError("only plain text messages allowed")
        result = {"model": CHAT_MODEL,
                  "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
                  "max_tokens": 8192, "stream": False, "temperature": 0,
                  "reasoning": {"effort": "minimal"}}
        if "response_format" in payload:
            result["response_format"] = payload["response_format"]
    elif path == "/v1/embeddings":
        if payload.get("model") != EMBED_MODEL:
            raise ValueError("embedding model not authorized")
        inputs = payload.get("input")
        if isinstance(inputs, str):
            inputs = [inputs]
        if not isinstance(inputs, list) or not inputs or not all(isinstance(x, str) for x in inputs):
            raise ValueError("only text embeddings allowed")
        if len(inputs) > 32:
            raise ValueError("embedding batch exceeds trial limit")
        result = {"model": EMBED_MODEL, "input": inputs, "encoding_format": "float"}
        if "dimensions" in payload:
            if payload["dimensions"] not in {768, 1536, 3072}:
                raise ValueError("unsupported trial embedding dimension")
            result["dimensions"] = payload["dimensions"]
    else:
        raise ValueError("endpoint not authorized")
    # No plugins, tools, web search, alternate models, or client routing overrides.
    result["provider"] = {"allow_fallbacks": False, "require_parameters": True,
                          "max_price": {"prompt": 0.30, "completion": 2.50, "request": 0}}
    return result


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS attempts "
                       "(id INTEGER PRIMARY KEY, endpoint TEXT NOT NULL, outcome TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS settlements "
                       "(through_id INTEGER PRIMARY KEY, cumulative_cents INTEGER NOT NULL, "
                       "reason TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS billing_bounds "
                       "(through_id INTEGER PRIMARY KEY, cents INTEGER NOT NULL, reason TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS call_costs "
                       "(attempt_id INTEGER PRIMARY KEY, micro_usd INTEGER NOT NULL)")

    def record_upper_bound(self, through_id: int, cents: int, reason: str,
                           *, externally_confirmed_closed: bool = False) -> None:
        # Retain older mistaken reports; append the user's corrected cumulative bound.
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            count, complete = db.execute(
                "SELECT count(*), sum(outcome='completed') FROM attempts WHERE id<=?",
                (through_id,)).fetchone()
            if (type(through_id) is not int or through_id < 1 or count != through_id
                    or (complete != count and not externally_confirmed_closed)
                    or type(cents) is not int or not 0 <= cents <= 200
                    or not reason.strip()):
                raise ValueError("invalid cumulative billing bound")
            existing = db.execute("SELECT cents, reason FROM billing_bounds WHERE through_id=?",
                                  (through_id,)).fetchone()
            if existing and existing != (cents, reason):
                raise ValueError("billing bound is immutable")
            db.execute("INSERT OR IGNORE INTO billing_bounds VALUES (?, ?, ?)",
                       (through_id, cents, reason))

    def exposure(self, db):
        through, cents, _ = self.accounting(db)
        bound = db.execute("SELECT through_id, cents FROM billing_bounds "
                           "ORDER BY through_id DESC LIMIT 1").fetchone()
        bounded = bool(bound and bound[0] >= through)
        if bounded:
            through, cents = bound
        cost, unknown = db.execute(
            "SELECT coalesce(sum(c.micro_usd),0), sum(CASE WHEN c.attempt_id IS NULL THEN 1 ELSE 0 END) "
            "FROM attempts a LEFT JOIN call_costs c ON c.attempt_id=a.id WHERE a.id>?",
            (through,)).fetchone()
        return through, cents * 10000, cost, unknown or 0, bounded

    @staticmethod
    def accounting(db):
        row = db.execute("SELECT through_id, cumulative_cents FROM settlements "
                         "ORDER BY through_id DESC LIMIT 1").fetchone()
        through, actual = row or (0, 0)
        unsettled = db.execute("SELECT count(*) FROM attempts WHERE id > ?", (through,)).fetchone()[0]
        return through, actual, unsettled

    def settle(self, through_id: int, cumulative_cents: int, reason: str) -> None:
        """Record externally confirmed cumulative billing; never remove attempts."""
        if (type(through_id) is not int or through_id < 1
                or type(cumulative_cents) is not int or not 0 <= cumulative_cents <= CAP_CENTS
                or not reason.strip()):
            raise ValueError("invalid confirmed billing checkpoint")
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT cumulative_cents, reason FROM settlements WHERE through_id=?",
                                  (through_id,)).fetchone()
            if existing:
                if existing != (cumulative_cents, reason):
                    raise ValueError("confirmed checkpoint is immutable")
                return
            previous, actual, _ = self.accounting(db)
            total, completed = db.execute(
                "SELECT count(*), sum(CASE WHEN outcome='completed' THEN 1 ELSE 0 END) "
                "FROM attempts WHERE id <= ?", (through_id,)).fetchone()
            if (through_id <= previous or cumulative_cents < actual
                    or total != through_id or completed != total):
                raise ValueError("checkpoint must cover a completed contiguous prefix")
            db.execute("INSERT INTO settlements VALUES (?, ?, ?)",
                       (through_id, cumulative_cents, reason))

    def reserve(self, endpoint: str) -> int:
        with closing(sqlite3.connect(self.path, timeout=30)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            _, base, cost, unknown, _ = self.exposure(db)
            if base + cost + (unknown + 1) * 100000 > 2000000:
                raise ValueError("$2 trial reservation budget exhausted")
            cursor = db.execute("INSERT INTO attempts(endpoint) VALUES (?)", (endpoint,))
            return cursor.lastrowid

    def can_reserve(self) -> bool:
        """Read-only preflight; reserve still enforces the cap atomically."""
        with closing(sqlite3.connect(self.path)) as db:
            _, base, cost, unknown, _ = self.exposure(db)
        return base + cost + (unknown + 1) * 100000 <= 2000000

    def finish(self, identity: int, outcome: str, provider_cost=None) -> None:
        micro = None
        if outcome == "completed" and provider_cost is not None and not isinstance(provider_cost, bool):
            try:
                amount = Decimal(str(provider_cost))
                if amount.is_finite() and 0 <= amount <= 200:
                    micro = int((amount * 1000000).to_integral_value(rounding=ROUND_CEILING))
            except InvalidOperation:
                pass
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE attempts SET outcome=? WHERE id=?", (outcome, identity))
            if micro is not None:
                db.execute("INSERT OR IGNORE INTO call_costs VALUES (?, ?)", (identity, micro))

    def summary(self) -> dict:
        with closing(sqlite3.connect(self.path)) as db, db:
            count = db.execute("SELECT count(*) FROM attempts").fetchone()[0]
            through, base, cost, unknown, bounded = self.exposure(db)
        return {"attempts": count, "reserved_usd": unknown / 10, "cap_usd": 2,
                "checkpoint_through_attempt": through, "checkpoint_usd": base / 1000000,
                "checkpoint_is_upper_bound": bounded, "provider_reported_usd": cost / 1000000,
                "accounted_usd": (base + cost + unknown * 100000) / 1000000,
                "actual_cost_usd": (base + cost) / 1000000 if not bounded and not unknown else None}


def start_gateway(key: str, ledger: Ledger, local_token: str, *, allow_requests=True):
    # Bound simultaneous reservations as well as spend. Cognee can fan out dozens
    # of embeddings; queued requests must not consume reservations prematurely.
    slots = threading.BoundedSemaphore(2)
    reservations = threading.Condition()
    inflight = 0

    def reserve_when_available(endpoint):
        nonlocal inflight
        with reservations:
            while True:
                try:
                    identity = ledger.reserve(endpoint)
                    inflight += 1
                    return identity
                except ValueError:
                    if not inflight:
                        raise
                    # Existing requests may settle cheaply. Wait for their actual
                    # outcome instead of making Cognee retry a temporary shortage.
                    reservations.wait(timeout=125)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_json(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            with slots:
                self.forward_request()

        def forward_request(self):
            if not allow_requests:
                self.send_json(403, {"error": "provider calls disabled for local lifecycle check"})
                return
            if self.headers.get("Authorization") != f"Bearer {local_token}":
                self.send_json(401, {"error": "unauthorized trial caller"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BYTES:
                    raise ValueError("request size outside trial limit")
                payload = prepare(self.path, json.loads(self.rfile.read(size)))
                reservation = reserve_when_available(self.path)
            except (ValueError, TypeError, AttributeError) as error:
                self.send_json(400, {"error": str(error)})
                return
            request = urllib.request.Request(
                "https://openrouter.ai/api" + self.path,
                data=json.dumps(payload).encode(), method="POST",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = json.load(response)
                usage = data.get("usage") or {}
                ledger.finish(reservation, "completed", usage.get("cost") if isinstance(usage, dict) else None)
                self.send_json(200, data)
            except (OSError, ValueError):
                # Never refund a timeout: the provider may already have billed it.
                ledger.finish(reservation, "failed_or_uncertain")
                self.send_json(502, {"error": "upstream trial call failed; reservation retained"})
            finally:
                nonlocal inflight
                with reservations:
                    inflight -= 1
                    reservations.notify_all()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
