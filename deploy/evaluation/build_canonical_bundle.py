"""Build a graph-pilot bundle from canonical identity data alone.

No provider, no Cognee: records are current DM-only claims read from Campaign
Core; the graph is the identity association structure — Entity nodes from the
entities table, DocumentChunk nodes per current claim, "contains" edges from
each claim to its linked identities, entity-entity co-mention edges whose
shared chunk sources are the claims naming both, and the DM's explicit faction
structure — "member_of" edges from audited rosters (with any held role title)
and "leader_of" edges for unique leadership seats. This is the same bundle
shape the deployed GraphPilotRetrieval reads, derived from auditable records
instead of extracted text.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "campaign-core/src"))
sys.path.insert(0, str(ROOT / "campaign-core/.venv/Lib/site-packages"))
from dm_assistant_core.domain.models import ClaimState  # noqa: E402
from dm_assistant_core.domain.retrieval import RetrievalAuthority  # noqa: E402

RECORDS_IDS_SQL = """
SELECT coalesce(json_agg(row_to_json(x)), '[]'::json) FROM (
 SELECT c.id::text AS record_id
 FROM claims c
 WHERE c.state IN ('established','observed','intended','prepared')
   AND c.visibility = 'dm_only'
   AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
) x;
"""

ASSOC_SQL = """
SELECT coalesce(json_agg(row_to_json(x)), '[]'::json) FROM (
 SELECT c.id::text AS claim_id, e.id::text AS entity_id, e.canonical_name,
        e.entity_type, c.assertion_text,
        coalesce((SELECT json_agg(a.alias) FROM entity_aliases a
                  WHERE a.entity_id = e.id), '[]'::json) AS aliases
 FROM claims c
 JOIN claim_related_entities cre ON cre.claim_id = c.id
 JOIN entities e ON e.id = cre.entity_id
 WHERE c.state IN ('established','observed','intended','prepared')
   AND c.visibility = 'dm_only'
   AND NOT EXISTS (SELECT 1 FROM claim_supersessions cs WHERE cs.superseded_claim_id = c.id)
) x;
"""

ROSTER_SQL = """
SELECT coalesce(json_agg(row_to_json(x)), '[]'::json) FROM (
 SELECT mr.member_id::text AS member_id, mr.faction_id::text AS faction_id,
        mr.role_title,
        coalesce(fr.is_leadership, false) AS is_leadership
 FROM membership_records mr
 JOIN entities f ON f.id = mr.faction_id
 LEFT JOIN faction_roles fr ON fr.faction_id = mr.faction_id AND fr.name = mr.role_title
 WHERE mr.superseded_by IS NULL
) x;
"""


def psql_json(sql):
    result = subprocess.run([
        "docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X", "-t", "-A",
        "-U", "campaign_owner", "-d", "campaign", "-v", "ON_ERROR_STOP=1",
        "-c", "BEGIN READ ONLY; " + sql + " ROLLBACK;",
    ], capture_output=True, text=True, encoding="utf-8", check=True)
    body = result.stdout.removeprefix("BEGIN\n").removesuffix("ROLLBACK\n").strip()
    return json.loads(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", default="live-pilot-v5")
    args = parser.parse_args()
    runtime = ROOT / ".local/cognee-evaluation"
    output_dir = runtime / args.generation
    output_dir.mkdir(parents=True, exist_ok=True)

    # Records come through the same adapter transform Core uses, so the
    # pilot's fingerprint revalidation matches exactly (visibility, source_id,
    # entity enrichment, recorded_at format).
    from unittest.mock import MagicMock
    from datetime import datetime
    from uuid import UUID
    from dm_assistant_core.adapters.postgres.retrieval import PostgresRetrievalRepository
    from dm_assistant_core.domain.retrieval import RetrievalQuery

    ids_raw = psql_json(RECORDS_IDS_SQL)
    database = MagicMock()
    connection = database.connection.return_value.__enter__.return_value
    connection.execute.return_value.fetchall.return_value = []
    repository = PostgresRetrievalRepository(database)
    repository.current_records(
        RetrievalQuery(question="pilot", requester_visibility={"role": "dm"}),
        tuple(r["record_id"] for r in ids_raw))
    captured = connection.execute.call_args
    rendered = captured.args[0]
    params = captured.args[1]
    values = params[0] if len(params) == 1 and isinstance(params[0], (list, tuple)) else params
    ids = ",".join("'" + str(value) + "'" for value in values)
    rendered = rendered.replace("%s", f"ARRAY[{ids}]::uuid[]")
    sql = "BEGIN READ ONLY;\nSELECT json_agg(row_to_json(x)) FROM (" + rendered + ") x;\nROLLBACK;"
    result = subprocess.run([
        "docker", "exec", "-i", "dm-assistant-campaign-db-1", "psql", "-X", "-t", "-A",
        "-U", "campaign_owner", "-d", "campaign", "-v", "ON_ERROR_STOP=1",
    ], input=sql, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError("records query failed: " + result.stderr.strip()[-300:])
    body = (result.stdout
            .removeprefix("BEGIN\n").removesuffix("ROLLBACK\n").strip())
    records = []
    for row in json.loads(body):
        values = list(row.values())
        if values[9] is not None:
            values[9] = datetime.fromisoformat(values[9])
        records.append(repository._to_record(values[:-1]).model_copy(
            update={"evidence_binding": values[-1]}))
    documents = {}
    for r in records:
        identity = str(uuid5(NAMESPACE_URL, f"dm-assistant/{args.generation}/{r.record_id}"))
        documents[identity] = {"record_id": r.record_id, "text": r.assertion}

    assoc = psql_json(ASSOC_SQL)
    by_claim = {}
    entities = {}
    for link in assoc:
        entities[link["entity_id"]] = (link["canonical_name"], link["entity_type"],
                                       link.get("aliases") or [])
        by_claim.setdefault(link["claim_id"], []).append(link["entity_id"])

    # Explicit rosters are canonical structure, not co-mention inference: a
    # member_of edge for every audited seat (with the held role title), plus a
    # leader_of edge for unique leadership seats. These edges exist even when
    # no claim co-mentions the member with the faction.
    roster = psql_json(ROSTER_SQL)
    member_edges = 0
    leader_edges = 0
    roster_edges = []
    for seat in roster:
        attrs = {"role": seat["role_title"]} if seat["role_title"] else {}
        roster_edges.append([seat["member_id"], seat["faction_id"], "member_of", attrs])
        member_edges += 1
        if seat["role_title"] and seat["is_leadership"]:
            roster_edges.append([seat["member_id"], seat["faction_id"], "leader_of",
                                 {"role": seat["role_title"]}])
            leader_edges += 1
    for edge in roster_edges:
        for endpoint in (edge[0], edge[1]):
            if endpoint not in entities:
                entities[endpoint] = None

    nodes = [[entity_id, {"type": "Entity", "name": name, "entity_type": kind,
                           "aliases": aliases}]
             for entity_id, (name, kind, aliases) in entities.items() if entities[entity_id]]
    edges = []
    seen_pairs = set()
    for claim_id, entity_ids in by_claim.items():
        chunk = next(doc_id for doc_id, doc in documents.items()
                     if doc["record_id"] == claim_id)
        for entity_id in entity_ids:
            nodes.append([chunk, {"type": "DocumentChunk", "document_id": chunk,
                                  "text": documents[chunk]["text"]}])
            edges.append([chunk, entity_id, "contains", {}])
        unique = sorted(set(entity_ids))
        for i, left in enumerate(unique):
            for right in unique[i + 1:]:
                pair = (left, right, claim_id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                edges.append([left, right, "co_mention", {}])
    edges.extend(roster_edges)

    bundle = {"records": [r.model_dump(mode="json") for r in records],
              "documents": documents, "graph": [nodes, edges]}
    (output_dir / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
    summary = {"records": len(records), "entities": len(entities),
               "linked_claims": len(by_claim), "edges": len(edges),
               "member_edges": member_edges, "leader_edges": leader_edges}
    (output_dir / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
