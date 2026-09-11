import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import NAMESPACE_URL, uuid5

from cross_document_trial import DATASET, replace_geography, retire_geography


class RetirementTests(unittest.IsolatedAsyncioTestCase):
    async def test_replacement_queries_before_and_after_and_uses_new_revision(self):
        sdk = SimpleNamespace(
            datasets=SimpleNamespace(
                list_datasets=AsyncMock(return_value=[SimpleNamespace(name=DATASET, id="dataset")]),
                list_data=AsyncMock(return_value=[])),
            search=AsyncMock(side_effect=[["retired context"], ["corrected context"]]),
            add=AsyncMock(), cognify=AsyncMock())
        modules = {
            "cognee.infrastructure.databases.graph": SimpleNamespace(
                get_graph_engine=AsyncMock(return_value=SimpleNamespace(get_graph_data=AsyncMock()))),
            "cognee.modules.search.types": SimpleNamespace(SearchType=SimpleNamespace(GRAPH_COMPLETION="graph")),
            "cognee.tasks.ingestion.data_item": SimpleNamespace(DataItem=SimpleNamespace),
        }
        report = {}
        with patch.dict(sys.modules, modules):
            await replace_geography(sdk, report)
        item = sdk.add.call_args.args[0]
        self.assertEqual(item.external_metadata, {"source_id": "geography", "revision": "r2"})
        self.assertIn("Southreach", item.data)
        self.assertEqual([q["stage"] for q in report["queries"]], ["retired", "replaced"])
        for call in sdk.search.call_args_list:
            self.assertTrue(call.kwargs["only_context"])

    def setup_probe(self, identity=None):
        target = SimpleNamespace(
            id=identity or uuid5(NAMESPACE_URL, "dm-assistant-eval/geography/r1"),
            external_metadata={"source_id": "geography", "revision": "r1"})
        sdk = SimpleNamespace(datasets=SimpleNamespace(
            list_datasets=AsyncMock(return_value=[SimpleNamespace(name=DATASET, id="dataset")]),
            list_data=AsyncMock(side_effect=[[target], []]),
            delete_data=AsyncMock(return_value={"status": "success"})))
        graph = SimpleNamespace(get_graph_data=AsyncMock(side_effect=[[["before"]], [[]]]))
        module = SimpleNamespace(get_graph_engine=AsyncMock(return_value=graph))
        return sdk, module, target

    async def test_deletes_only_verified_source_and_preserves_report(self):
        sdk, module, target = self.setup_probe()
        report = {}
        with patch.dict(sys.modules, {"cognee.infrastructure.databases.graph": module}):
            await retire_geography(sdk, report)
        sdk.datasets.delete_data.assert_awaited_once_with(
            dataset_id="dataset", data_id=target.id, mode="soft")
        self.assertEqual(report["before_graph"], [["before"]])
        self.assertIn("Northreach", report["retired_source"]["preserved_original_text"])

    async def test_wrong_identity_is_not_deleted(self):
        sdk, module, _ = self.setup_probe(identity="wrong-id")
        with (patch.dict(sys.modules, {"cognee.infrastructure.databases.graph": module}),
              self.assertRaises(ValueError)):
            await retire_geography(sdk, {})
        sdk.datasets.delete_data.assert_not_awaited()

    async def test_missing_source_is_not_deleted(self):
        sdk, module, _ = self.setup_probe()
        sdk.datasets.list_data.side_effect = [[]]
        with (patch.dict(sys.modules, {"cognee.infrastructure.databases.graph": module}),
              self.assertRaises(ValueError)):
            await retire_geography(sdk, {})
        sdk.datasets.delete_data.assert_not_awaited()
