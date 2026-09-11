"""Add the two focused, source-backed Ruhrogue character projections."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb


NAMESPACE = UUID("4f227b1a-906d-43a5-9b5d-2165074df5fe")
REPAIR_KEY = "starfall:ruhrogue-character-claims:v1"
RUHROGUE_ID = UUID("b6f72956-f065-4c68-b2d5-05f1f30c9316")


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
        claim_ids = (stable("claim:chamber"), stable("claim:return-to-camp"))
        existing = connection.execute(
            "SELECT id FROM claims WHERE id = ANY(%s)", (list(claim_ids),)
        ).fetchall()
        if len(existing) == 2:
            print(json.dumps({"outcome": "already_applied", "claims": [str(value) for value in claim_ids]}))
            return
        if existing:
            raise SystemExit(f"partial prior repair detected: {existing}")

        evidence = {}
        for path in ("sessions/notes/2026-05-09.md", "sessions/notes/2026-06-06.md"):
            row = connection.execute(
                "SELECT ss.id FROM source_document_paths sdp "
                "JOIN source_revisions sr ON sr.source_document_id=sdp.source_document_id "
                "JOIN source_spans ss ON ss.source_revision_id=sr.id "
                "WHERE sdp.normalized_path=%s AND sdp.is_current "
                "ORDER BY sr.captured_at DESC, (ss.end_offset-ss.start_offset) DESC LIMIT 1",
                (path,),
            ).fetchone()
            if row is None:
                raise SystemExit(f"source evidence span not found: {path}")
            evidence[path] = row[0]

        claims = (
            {
                "id": str(claim_ids[0]),
                "subject_entity_id": str(RUHROGUE_ID),
                "predicate": None,
                "object_entity_id": None,
                "assertion_text": (
                    "Ruhrogue passed his Chamber of Echoes trial after seeing visions of leaving his "
                    "homeland, returning and being chased out again, fleeing with rebels to the exile "
                    "camp, making tentative peace with exiles from Goodman's City, and acknowledging "
                    "that tragedy can force people to work together and trust each other."
                ),
                "state": "observed", "authority": "real_play", "confidence": "1",
                "visibility": "dm_only", "is_conditional": False,
                "predicts_subject_action": False, "recorded_at": now.isoformat(),
                "observed_year": 2026, "observed_month": 5, "observed_day": 9,
                "campaign_calendar_id": "gregorian-ce",
                "source_span_id": str(evidence["sessions/notes/2026-05-09.md"]),
                "evidence_role": "support",
                "repair_reason": "Project the focused Ruhrogue real-play outcome from its session evidence.",
            },
            {
                "id": str(claim_ids[1]),
                "subject_entity_id": str(RUHROGUE_ID),
                "predicate": None,
                "object_entity_id": None,
                "assertion_text": "Ruhrogue wanted to return to camp and assemble an army to assault Fleurite Castle.",
                "state": "intended", "authority": "real_play", "confidence": "1",
                "visibility": "dm_only", "is_conditional": False,
                "predicts_subject_action": False, "recorded_at": now.isoformat(),
                "campaign_calendar_id": "gregorian-ce",
                "source_span_id": str(evidence["sessions/notes/2026-06-06.md"]),
                "evidence_role": "support",
                "repair_reason": "Record a player-communicated plan without predicting future PC action.",
            },
        )
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
