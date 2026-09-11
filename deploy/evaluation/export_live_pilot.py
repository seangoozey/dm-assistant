"""Read-only export of a small, explicitly authorized DM-only graph pilot."""
import argparse
import json
import subprocess
from pathlib import Path

SQL = """
SELECT coalesce(json_agg(row_to_json(x)), '[]'::json) FROM (
 SELECT c.id AS record_id, c.assertion_text AS assertion, c.state, c.authority,
 c.visibility,
 (SELECT json_agg(json_build_object('span_id', ss.id, 'revision_id', sr.id,
 'content_hash',sr.content_hash,'start',ss.start_offset,'end',ss.end_offset,
 'citation',sd.original_path || '#' || coalesce(ss.section_path,'')))
 FROM claim_evidence ce JOIN source_spans ss ON ss.id=ce.source_span_id
 JOIN source_revisions sr ON sr.id=ss.source_revision_id
 JOIN source_documents sd ON sd.id=sr.source_document_id WHERE ce.claim_id=c.id) AS evidence
 FROM claims c WHERE c.state IN ('established','observed','intended','prepared')
 AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id=c.id)
 AND c.assertion_text ~* '(Tsunadis|Ishi.{0,2}go.{0,2}dan|Ragga.{0,2}na.{0,2}ken)'
 AND length(c.assertion_text) <= 7000
 ORDER BY (c.assertion_text ~* 'Tsunadis') DESC,
 (c.assertion_text ~* 'Ragga.{0,2}na.{0,2}ken') DESC, length(c.assertion_text), c.id LIMIT 12
) x;
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", choices=["live-pilot-v2", "live-pilot-v3"], default="live-pilot-v2")
    args = parser.parse_args()
    sql = SQL if args.generation == "live-pilot-v2" else SQL.replace("LIMIT 12", "LIMIT 64")
    result = subprocess.run([
        "docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X", "-t", "-A",
        "-U", "campaign_owner", "-d", "campaign", "-v", "ON_ERROR_STOP=1",
        "-c", "BEGIN READ ONLY; " + sql + " ROLLBACK;",
    ], capture_output=True, text=True, encoding="utf-8", check=True)
    payload = result.stdout.removeprefix("BEGIN\n").removesuffix("ROLLBACK\n").strip()
    records = json.loads(payload)
    if not records or any(not r["evidence"] for r in records):
        raise RuntimeError("Pilot must contain evidenced claims")
    output = Path(__file__).resolve().parents[2] / f".local/cognee-evaluation/{args.generation}-input.json"
    if output.exists():
        raise RuntimeError("Existing pilot snapshot retained; choose a new generation explicitly")
    output.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(records), "assertion_chars": sum(
        len(r["assertion"]) for r in records), "output": str(output)}))
