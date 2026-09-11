"""One-time, idempotent canonicalization of the three source-only Starfall PCs."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb


NAMESPACE = UUID("4f227b1a-906d-43a5-9b5d-2165074df5fe")
REPAIR_KEY = "starfall:canonicalize-missing-pcs:v1"
PCS = (
    ("Coreferra", "pcs/coreferra.md"),
    ("Ladir", "pcs/ladir.md"),
    ("Zander Thromius", "pcs/zander-thromius.md"),
)


def stable(label: str) -> UUID:
    return uuid5(NAMESPACE, f"{REPAIR_KEY}:{label}")


def main() -> None:
    now = datetime.now(UTC)
    workflow_id = stable("workflow")
    proposal_id = stable("proposal")
    version_id = stable("version:1")
    approval_id = stable("approval:1")
    change_set_id = stable("change-set")

    with psycopg.connect(os.environ["CAMPAIGN_DATABASE_URL"]) as connection:
        existing = {
            str(row[0]): row[1]
            for row in connection.execute(
                "SELECT canonical_name, id FROM entities WHERE entity_type='pc' "
                "AND lower(canonical_name) = ANY(%s)",
                ([name.casefold() for name, _ in PCS],),
            ).fetchall()
        }
        missing = [(name, path) for name, path in PCS if name not in existing]
        if not missing:
            print(json.dumps({"outcome": "already_applied", "entities": existing}, default=str))
            return
        if len(missing) != len(PCS):
            raise SystemExit(f"partial prior repair detected; existing={existing}")

        items = []
        for sequence, (name, path) in enumerate(PCS, start=1):
            source = connection.execute(
                "SELECT sd.id, sr.id FROM source_document_paths sdp "
                "JOIN source_documents sd ON sd.id=sdp.source_document_id "
                "JOIN LATERAL (SELECT id FROM source_revisions WHERE source_document_id=sd.id "
                "ORDER BY captured_at DESC, id DESC LIMIT 1) sr ON true "
                "WHERE sdp.normalized_path=%s",
                (path,),
            ).fetchone()
            if source is None:
                raise SystemExit(f"authoritative PC source not found: {path}")
            target_id = stable(f"entity:{name}")
            item_id = stable(f"item:{sequence}:{name}")
            after = {
                "id": str(target_id), "record_type": "entity", "entity_kind": "pc",
                "entity_kind_version": 1, "entity_type": "pc", "canonical_name": name,
                "tags": [], "source_document_id": str(source[0]),
                "source_revision_id": str(source[1]),
                "repair_reason": "Complete canonical PC identity coverage after migration closure audit.",
            }
            items.append((item_id, sequence, target_id, after))

        reviewed = [{"item_id": str(item[0]), "sequence": item[1], "target_id": str(item[2]), "after": item[3]} for item in items]
        content_hash = hashlib.sha256(json.dumps(reviewed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        connection.execute("INSERT INTO workflow_sessions(id,kind,started_at,closed_at) VALUES (%s,'lore_entry',%s,%s)", (workflow_id, now, now))
        connection.execute("INSERT INTO proposals(id,workflow_session_id,status,created_at) VALUES (%s,%s,'pending',%s)", (proposal_id, workflow_id, now))
        connection.execute("INSERT INTO proposal_versions(id,proposal_id,version_number,content_hash,created_at) VALUES (%s,%s,1,%s,%s)", (version_id, proposal_id, content_hash, now))
        for item_id, sequence, target_id, after in items:
            connection.execute("INSERT INTO proposal_items(id,proposal_version_id,sequence,mutation_kind,target_type,target_id,after_json) VALUES (%s,%s,%s,'create_entity','entity',%s,%s)", (item_id, version_id, sequence, target_id, Jsonb(after)))
        connection.execute("INSERT INTO approvals(id,proposal_version_id,scope_json,approved_at) VALUES (%s,%s,%s,%s)", (approval_id, version_id, Jsonb([str(item[0]) for item in items]), now))
        connection.execute("INSERT INTO change_sets(id,idempotency_key,workflow_session_id,proposal_version_id,status,requested_at) VALUES (%s,%s,%s,%s,'pending',%s)", (change_set_id, REPAIR_KEY, workflow_id, version_id, now))
        receipt = connection.execute("SELECT apply_campaign_change_set(%s,1,%s,%s)", (change_set_id, approval_id, content_hash)).fetchone()
        assert receipt is not None
        print(json.dumps({"outcome": "applied", "receipt": receipt[0], "entities": {name: str(stable(f'entity:{name}')) for name, _ in PCS}}, default=str))


if __name__ == "__main__":
    main()
