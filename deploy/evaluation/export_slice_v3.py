"""Read-only export of the Romulus-neighborhood slice for the v3 live evaluation.

Same pattern as export_live_pilot.py: one READ-ONLY transaction through
`docker exec psql` against the campaign database. No writes, no credentials
beyond the existing local container. Canonical claims only (promoted, current,
DM-only), each with its real state/authority/visibility and canonical entity
associations for identity resolution. Output stays in ignored local storage.
"""
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
 JOIN source_documents sd ON sd.id=sr.source_document_id WHERE ce.claim_id=c.id) AS evidence,
 (SELECT json_agg(DISTINCT e.canonical_name) FROM claim_related_entities cre
 JOIN entities e ON e.id=cre.entity_id WHERE cre.claim_id=c.id) AS entities
 FROM claims c WHERE c.state IN ('established','observed','intended','prepared')
 AND c.visibility = 'dm_only'
 AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id=c.id)
 AND c.assertion_text ~* '(Romulus|Inquisition|Eustice|Sorin|Outrider|Arkin|ley ?line|Monaster)'
 AND length(c.assertion_text) <= 7000
 ORDER BY (c.assertion_text ~* 'Romulus') DESC,
 (c.assertion_text ~* '(Eustice|Sorin|Outrider)') DESC,
 (c.assertion_text ~* 'Monaster') DESC, length(c.assertion_text), c.id LIMIT 40
) x;
"""

if __name__ == "__main__":
    result = subprocess.run([
        "docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X", "-t", "-A",
        "-U", "campaign_owner", "-d", "campaign", "-v", "ON_ERROR_STOP=1",
        "-c", "BEGIN READ ONLY; " + SQL + " ROLLBACK;",
    ], capture_output=True, text=True, encoding="utf-8", check=True)
    payload = result.stdout.removeprefix("BEGIN\n").removesuffix("ROLLBACK\n").strip()
    records = json.loads(payload)
    if not records or any(not r["evidence"] for r in records):
        raise RuntimeError("Slice must contain evidenced claims")
    output = Path(__file__).resolve().parents[2] / ".local/cognee-evaluation/relevance-v3-slice-input.json"
    output.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(records),
                      "states": sorted({r["state"] for r in records}),
                      "with_entities": sum(1 for r in records if r["entities"]),
                      "eustice_sorin_outrider": sum(
                          1 for r in records
                          if any(t in (r["assertion"] or "").lower()
                                 for t in ("eustice", "sorin", "outrider")))}))
