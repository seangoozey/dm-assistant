import copy
import json
import unittest
from pathlib import Path

from corpus_trial import inputs


class CorpusTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[2] / "tests/fixtures/connected_knowledge_cases.json"
        self.corpus = json.loads(path.read_text())

    def test_inputs_are_independent_of_gold_answers(self):
        modified = copy.deepcopy(self.corpus)
        for case in modified["cases"]:
            for key in ("required_ids", "required_paths", "forbidden_ids", "forbidden_support_ids", "forbidden_paths"):
                case[key] = ["changed"]
            case["expected_mode"] = "changed"
        for scope in ("dm", "party", "conflict"):
            self.assertEqual(inputs(self.corpus, scope), inputs(modified, scope))

    def test_scope_excludes_hidden_and_superseded_before_indexing(self):
        records, _ = inputs(self.corpus, "party")
        self.assertTrue(all(r["visibility"] == "party" and r["state"] != "superseded" for r in records))
        self.assertNotIn("contradiction", [r["record_id"] for r in records])

    def test_all_cases_partition_once(self):
        cases = [c["id"] for scope in ("dm", "party", "conflict") for c in inputs(self.corpus, scope)[1]]
        self.assertEqual(len(cases), 24)
        self.assertEqual(len(set(cases)), 24)
