"""Add focused Chamber of Echoes outcomes for Coreferra, Ladir, and Zander."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb


NAMESPACE = UUID("4f227b1a-906d-43a5-9b5d-2165074df5fe")
REPAIR_KEY = "starfall:other-pc-chamber-claims:v1"
PCS = (
    (
        "Coreferra",
        UUID("485b8d23-7789-5fc0-a969-5e3b959967e4"),
        "Coreferra passed his Chamber of Echoes trial after directing the mirror's visions "
        "to examine his past and present. He accepted that his journey does not end whether "
        "or not his brother is saved, because the act of searching has transformed him.",
    ),
    (
        "Ladir",
        UUID("ca573abb-135f-5918-aaf4-89de64a258fe"),
        "Ladir passed his Chamber of Echoes trial after seeing a vision in which his clan "
        "welcomed him home while the world was being destroyed. He chose to leave home and "
        "save the world instead of settling into comfortable belonging.",
    ),
    (
        "Zander Thromius",
        UUID("1056e617-2011-5de7-b77d-6a8bd256eb3f"),
        "Zander Thromius passed his Chamber of Echoes trial after discussing a never-ending "
        "journey with his mirror self. He realized that his journey does have a destination: "
        "self-discovery.",
    ),
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
    claim_ids = tuple(stable(f"claim:{name}") for name, _, _ in PCS)

    with psycopg.connect(os.environ["CAMPAIGN_DATABASE_URL"]) as connection:
        existing = connection.execute(
            "SELECT id FROM claims WHERE id = ANY(%s)", (list(claim_ids),)
        ).fetchall()
        if len(existing) == len(PCS):
            print(json.dumps({"outcome": "already_applied", "claims": [str(value) for value in claim_ids]}))
            return
        if existing:
            raise SystemExit(f"partial prior repair detected: {existing}")

        source_span = connection.execute(
            "SELECT ss.id FROM source_document_paths sdp "
            "JOIN source_revisions sr ON sr.source_document_id=sdp.source_document_id "
            "JOIN source_spans ss ON ss.source_revision_id=sr.id "
            "WHERE sdp.normalized_path='sessions/notes/2026-05-09.md' AND sdp.is_current "
            "ORDER BY sr.captured_at DESC, (ss.end_offset-ss.start_offset) DESC LIMIT 1"
        ).fetchone()
        if source_span is None:
            raise SystemExit("Chamber of Echoes session evidence span not found")

        claims = []
        for claim_id, (name, entity_id, assertion) in zip(claim_ids, PCS, strict=True):
            claims.append({
                "id": str(claim_id), "subject_entity_id": str(entity_id),
                "predicate": None, "object_entity_id": None, "assertion_text": assertion,
                "state": "observed", "authority": "real_play", "confidence": "1",
                "visibility": "dm_only", "is_conditional": False,
                "predicts_subject_action": False, "recorded_at": now.isoformat(),
                "observed_year": 2026, "observed_month": 5, "observed_day": 9,
                "campaign_calendar_id": "gregorian-ce", "source_span_id": str(source_span[0]),
                "evidence_role": "support",
                "repair_reason": f"Project {name}'s focused Chamber of Echoes outcome from session evidence.",
            })

        reviewed = [{"sequence": index, "after": claim} for index, claim in enumerate(claims, 1)]
        content_hash = hashlib.sha256(json.dumps(reviewed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        connection.execute("INSERT INTO workflow_sessions(id,kind,started_at,closed_at) VALUES (%s,'lore_entry',%s,%s)", (workflow_id, now, now))
        connection.execute("INSERT INTO proposals(id,workflow_session_id,status,created_at) VALUES (%s,%s,'pending',%s)", (proposal_id, workflow_id, now))
        connection.execute("INSERT INTO proposal_versions(id,proposal_id,version_number,content_hash,created_at) VALUES (%s,%s,1,%s,%s)", (version_id, proposal_id, content_hash, now))
        item_ids = []
        for sequence, claim in enumerate(claims, 1):
            item_id = stable(f"item:{sequence}")
            item_ids.append(item_id)
            connection.execute(
                "INSERT INTO proposal_items(id,proposal_version_id,sequence,mutation_kind,target_type,target_id,after_json) "
                "VALUES (%s,%s,%s,'create_claim','claim',%s,%s)",
                (item_id, version_id, sequence, UUID(claim["id"]), Jsonb(claim)),
            )
        connection.execute("INSERT INTO approvals(id,proposal_version_id,scope_json,approved_at) VALUES (%s,%s,%s,%s)", (approval_id, version_id, Jsonb([str(value) for value in item_ids]), now))
        connection.execute("INSERT INTO change_sets(id,idempotency_key,workflow_session_id,proposal_version_id,status,requested_at) VALUES (%s,%s,%s,%s,'pending',%s)", (change_set_id, REPAIR_KEY, workflow_id, version_id, now))
        receipt = connection.execute("SELECT apply_campaign_change_set(%s,1,%s,%s)", (change_set_id, approval_id, content_hash)).fetchone()
        assert receipt is not None
        print(json.dumps({"outcome": "applied", "receipt": str(receipt[0]), "claims": [str(value) for value in claim_ids]}))


if __name__ == "__main__":
    main()
