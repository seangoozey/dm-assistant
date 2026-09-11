"""Add Coreferra's Herald of Arkin real-play fact from the 2026-06-20 notes."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb


NAMESPACE = UUID("4f227b1a-906d-43a5-9b5d-2165074df5fe")
REPAIR_KEY = "starfall:coreferra-herald-real-play:v1"
COREFERRA_ID = UUID("485b8d23-7789-5fc0-a969-5e3b959967e4")
SOURCE_PATH = "sessions/notes/2026-06-20.md"
ASSERTION = "Coreferra became the Herald of Arkin."


def stable(label: str) -> UUID:
    return uuid5(NAMESPACE, f"{REPAIR_KEY}:{label}")


def main() -> None:
    now = datetime.now(UTC)
    claim_id = stable("claim")
    workflow_id = stable("workflow")
    proposal_id = stable("proposal")
    version_id = stable("version:1")
    approval_id = stable("approval:1")
    change_set_id = stable("change-set")
    item_id = stable("item:1")

    with psycopg.connect(os.environ["CAMPAIGN_DATABASE_URL"]) as connection:
        if connection.execute("SELECT 1 FROM claims WHERE id=%s", (claim_id,)).fetchone():
            print(json.dumps({"outcome": "already_applied", "claim": str(claim_id)}))
            return

        source_span = connection.execute(
            "SELECT ss.id FROM source_document_paths sdp "
            "JOIN source_revisions sr ON sr.source_document_id=sdp.source_document_id "
            "JOIN source_spans ss ON ss.source_revision_id=sr.id "
            "WHERE sdp.normalized_path=%s AND sdp.is_current "
            "AND position('Coreferra became the Herald of Arkin' in convert_from(sr.raw_content,'UTF8'))-1 "
            "BETWEEN ss.start_offset AND ss.end_offset "
            "ORDER BY sr.captured_at DESC, (ss.end_offset-ss.start_offset) ASC LIMIT 1",
            (SOURCE_PATH,),
        ).fetchone()
        if source_span is None:
            raise SystemExit("exact Herald of Arkin session evidence span not found")

        claim = {
            "id": str(claim_id),
            "subject_entity_id": str(COREFERRA_ID),
            "predicate": None,
            "object_entity_id": None,
            "assertion_text": ASSERTION,
            "state": "observed",
            "authority": "real_play",
            "confidence": "1",
            "visibility": "dm_only",
            "is_conditional": False,
            "predicts_subject_action": False,
            "recorded_at": now.isoformat(),
            "observed_year": 2026,
            "observed_month": 6,
            "observed_day": 20,
            "campaign_calendar_id": "gregorian-ce",
            "source_span_id": str(source_span[0]),
            "evidence_role": "support",
            "repair_reason": "Project the June 20 observed outcome onto Coreferra's character record.",
        }
        reviewed = [{"sequence": 1, "after": claim}]
        content_hash = hashlib.sha256(
            json.dumps(reviewed, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        connection.execute(
            "INSERT INTO workflow_sessions(id,kind,started_at,closed_at) VALUES (%s,'lore_entry',%s,%s)",
            (workflow_id, now, now),
        )
        connection.execute(
            "INSERT INTO proposals(id,workflow_session_id,status,created_at) VALUES (%s,%s,'pending',%s)",
            (proposal_id, workflow_id, now),
        )
        connection.execute(
            "INSERT INTO proposal_versions(id,proposal_id,version_number,content_hash,created_at) VALUES (%s,%s,1,%s,%s)",
            (version_id, proposal_id, content_hash, now),
        )
        connection.execute(
            "INSERT INTO proposal_items(id,proposal_version_id,sequence,mutation_kind,target_type,target_id,after_json) "
            "VALUES (%s,%s,1,'create_claim','claim',%s,%s)",
            (item_id, version_id, claim_id, Jsonb(claim)),
        )
        connection.execute(
            "INSERT INTO approvals(id,proposal_version_id,scope_json,approved_at) VALUES (%s,%s,%s,%s)",
            (approval_id, version_id, Jsonb([str(item_id)]), now),
        )
        connection.execute(
            "INSERT INTO change_sets(id,idempotency_key,workflow_session_id,proposal_version_id,status,requested_at) "
            "VALUES (%s,%s,%s,%s,'pending',%s)",
            (change_set_id, REPAIR_KEY, workflow_id, version_id, now),
        )
        receipt = connection.execute(
            "SELECT apply_campaign_change_set(%s,1,%s,%s)",
            (change_set_id, approval_id, content_hash),
        ).fetchone()
        assert receipt is not None
        print(json.dumps({"outcome": "applied", "receipt": str(receipt[0]), "claim": str(claim_id)}))


if __name__ == "__main__":
    main()
