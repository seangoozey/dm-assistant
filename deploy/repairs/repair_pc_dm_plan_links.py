"""Replace unlinked migrated PC GM plans with focused entity-linked claims."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from uuid import UUID, uuid5

import psycopg
from psycopg.types.json import Jsonb


NAMESPACE = UUID("4f227b1a-906d-43a5-9b5d-2165074df5fe")
REPAIR_KEY = "starfall:link-pc-dm-plans:v1"
PLANS = (
    (
        "coreferra-role", UUID("485b8d23-7789-5fc0-a969-5e3b959967e4"),
        UUID("dc730598-6c0f-47a1-a5cd-85cf16ccb246"),
        "Coreferra may repair the broken flow of magic and restore Myrin's ley-line network after the inflection point is destroyed.",
    ),
    (
        "ladir-role", UUID("ca573abb-135f-5918-aaf4-89de64a258fe"),
        UUID("0e93505e-bde6-4cc6-b5f3-091b8c909b00"),
        "Ladir may destroy the inflection point by gathering power from the four Aeon Stones and return the awakened Titans to their proper elemental planes, beginning with Ishi'go'dan.",
    ),
    (
        "ruhrogue-role", UUID("b6f72956-f065-4c68-b2d5-05f1f30c9316"),
        UUID("63ca2e5a-0dd6-4df1-8ce1-a8919b0fb01a"),
        "Ruhrogue may unite the peoples and nations of Myrin into a coalition capable of surviving Starfall and supporting the final effort.",
    ),
    (
        "zander-role", UUID("1056e617-2011-5de7-b77d-6a8bd256eb3f"),
        UUID("af2a294f-6fff-4732-9f16-3e19890c7347"),
        "Zander Thromius may confront the Far Realm aberrations and corrupted manifestations appearing throughout Myrin once synchronization begins.",
    ),
    (
        "zander-tattoo", UUID("1056e617-2011-5de7-b77d-6a8bd256eb3f"),
        UUID("99aecde5-1d0c-44b9-92df-5ff96146561e"),
        "Zander Thromius's tattoo is intended as longer-term foreshadowing and should not derail the campaign too early.",
    ),
)


def stable(label: str) -> UUID:
    return uuid5(NAMESPACE, f"{REPAIR_KEY}:{label}")


def main() -> None:
    now = datetime.now(UTC)
    workflow_id, proposal_id = stable("workflow"), stable("proposal")
    version_id, approval_id = stable("version:1"), stable("approval:1")
    change_set_id = stable("change-set")
    claim_ids = tuple(stable(f"claim:{key}") for key, *_ in PLANS)

    with psycopg.connect(os.environ["CAMPAIGN_DATABASE_URL"]) as connection:
        existing = connection.execute("SELECT id FROM claims WHERE id=ANY(%s)", (list(claim_ids),)).fetchall()
        if len(existing) == len(PLANS):
            print(json.dumps({"outcome": "already_applied", "claims": [str(value) for value in claim_ids]}))
            return
        if existing:
            raise SystemExit(f"partial prior repair detected: {existing}")

        claims = []
        for claim_id, (key, entity_id, old_claim_id, assertion) in zip(claim_ids, PLANS, strict=True):
            evidence = connection.execute(
                "SELECT source_span_id FROM claim_evidence WHERE claim_id=%s ORDER BY source_span_id LIMIT 1",
                (old_claim_id,),
            ).fetchone()
            if evidence is None:
                raise SystemExit(f"source evidence missing for {old_claim_id}")
            claims.append({
                "id": str(claim_id), "subject_entity_id": str(entity_id),
                "predicate": None, "object_entity_id": None, "assertion_text": assertion,
                "state": "possible", "authority": "brainstorm", "confidence": "1",
                "visibility": "dm_only", "is_conditional": False,
                "predicts_subject_action": False, "recorded_at": now.isoformat(),
                "source_span_id": str(evidence[0]), "evidence_role": "support",
                "repair_reason": f"Replace unlinked migrated PC GM plan {old_claim_id} with {key}.",
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
            connection.execute("INSERT INTO proposal_items(id,proposal_version_id,sequence,mutation_kind,target_type,target_id,after_json) VALUES (%s,%s,%s,'create_claim','claim',%s,%s)", (item_id, version_id, sequence, UUID(claim["id"]), Jsonb(claim)))
        connection.execute("INSERT INTO approvals(id,proposal_version_id,scope_json,approved_at) VALUES (%s,%s,%s,%s)", (approval_id, version_id, Jsonb([str(value) for value in item_ids]), now))
        connection.execute("INSERT INTO change_sets(id,idempotency_key,workflow_session_id,proposal_version_id,status,requested_at) VALUES (%s,%s,%s,%s,'pending',%s)", (change_set_id, REPAIR_KEY, workflow_id, version_id, now))
        receipt = connection.execute("SELECT apply_campaign_change_set(%s,1,%s,%s)", (change_set_id, approval_id, content_hash)).fetchone()
        assert receipt is not None
        print(json.dumps({"outcome": "applied", "receipt": str(receipt[0]), "claims": [str(value) for value in claim_ids]}))


if __name__ == "__main__":
    main()
