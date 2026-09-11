import unittest

from evidence_expansion import Source, expand


class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.graph = [
            [["e", {"type": "Entity", "description": "Unverified description"}],
             ["c1", {"type": "DocumentChunk", "document_id": "d1", "text": "Mara went to Port."}],
             ["c2", {"type": "DocumentChunk", "document_id": "d2", "text": "Port is on Island."}]],
            [["c1", "e", "contains", {}], ["c2", "e", "contains", {}]],
        ]
        self.manifest = {"d1": Source("dispatch", "r1", "Mara went to Port."),
                         "d2": Source("geography", "r2", "Port is on Island.")}

    def test_shared_entity_recovers_both_passages_with_offsets(self):
        result = expand(self.graph, ["c1", "e", "e"], self.manifest)
        self.assertEqual(len(result["passages"]), 2)
        self.assertEqual(result["passages"][1]["retrieval_path"], ["e", "c2"])
        for passage in result["passages"]:
            source = self.manifest[passage["document_id"]]
            self.assertEqual(source.text[passage["start"]:passage["end"]], passage["text"])

    def test_disallowed_or_superseded_document_is_excluded(self):
        del self.manifest["d2"]
        self.assertEqual(len(expand(self.graph, ["e"], self.manifest)["passages"]), 1)

    def test_generated_or_changed_text_is_not_evidence(self):
        self.graph[0][2][1]["text"] = "Port is elsewhere."
        result = expand(self.graph, ["e"], self.manifest)
        self.assertEqual(len(result["passages"]), 1)
        self.assertFalse(result["generated_descriptions_are_evidence"])

    def test_unknown_seed_and_limit(self):
        self.assertEqual(expand(self.graph, ["missing"], self.manifest)["passages"], [])
        self.assertTrue(expand(self.graph, ["e"], self.manifest, limit=1)["truncated"])
