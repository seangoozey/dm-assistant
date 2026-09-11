"""Bind existing graph to reread Core records; no provider or canonical writes."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
from uuid import NAMESPACE_URL, UUID, uuid5
from pilot_input import index_text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "campaign-core/src"))
from dm_assistant_core.adapters.postgres.retrieval import PostgresRetrievalRepository
from dm_assistant_core.domain.retrieval import RetrievalQuery


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", choices=["live-pilot-v2", "live-pilot-v3"], default="live-pilot-v2")
    args = parser.parse_args()
    runtime = ROOT / ".local/cognee-evaluation"
    original = json.loads((runtime / f"{args.generation}-input.json").read_text(encoding="utf-8"))
    database = MagicMock()
    connection = database.connection.return_value.__enter__.return_value
    connection.execute.return_value.fetchall.return_value = []
    repository = PostgresRetrievalRepository(database)
    repository.current_records(RetrievalQuery(question="pilot", requester_visibility={"role":"dm"}),
                               tuple(r["record_id"] for r in original))
    sql = connection.execute.call_args.args[0]
    ids = ",".join("'" + str(UUID(r["record_id"])) + "'" for r in original)
    sql = "SELECT json_agg(row_to_json(x)) FROM (" + sql.replace("%s", f"ARRAY[{ids}]") + ") x"
    result = subprocess.run(["docker", "exec", "dm-assistant-campaign-db-1", "psql",
        "-X", "-t", "-A", "-U", "campaign_owner", "-d", "campaign", "-v", "ON_ERROR_STOP=1",
        "-c", sql], capture_output=True, text=True, encoding="utf-8", check=True)
    records = []
    for row in json.loads(result.stdout):
        values = list(row.values())
        if values[9] is not None:
            values[9] = datetime.fromisoformat(values[9])
        records.append(repository._to_record(values[:-1]).model_copy(
            update={"evidence_binding": values[-1]}))
    indexed = {r["record_id"]: r for r in original}
    if len(records) != len(original):
        raise ValueError("Pilot source set changed")
    documents = {}
    for r in records:
        source = indexed[r.record_id]
        # Bind only if both text and every source revision/offset still match.
        expected = {f"{e['span_id']}:{e['revision_id']}:{e['content_hash']}:{e['start']}:{e['end']}"
                    for e in source["evidence"]}
        actual = {e.rsplit(':', 1)[0] for e in (r.evidence_binding or '').split(',')}
        if r.assertion != source["assertion"] or expected != actual:
            raise ValueError("Pilot source evidence changed; rebuild required")
        revision = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
        identity = str(uuid5(NAMESPACE_URL, f"dm-assistant/live-pilot/{r.record_id}/{revision}"))
        documents[identity] = {"record_id": r.record_id, "text": index_text(source, args.generation)}
    graph = json.loads((runtime / args.generation / "graph.json").read_text(encoding="utf-8"))
    output = runtime / args.generation / "bundle.json"
    output.write_text(json.dumps({"records": [r.model_dump(mode="json") for r in records],
                                  "documents": documents, "graph": graph}), encoding="utf-8")
    print(f"Bound {len(records)} current Core records to pilot graph")


if __name__ == "__main__":
    main()
