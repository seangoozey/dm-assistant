"""Reclassify Oracles and Circle of Dreams to worldbuilding (Sean's ruling,
2026-09-13) through the same audited propose/approve/apply path the UI uses."""

import json
import time
import urllib.request

BASE = "http://127.0.0.1:8001"
TARGETS = [
    ("Oracles", "134b7269-fce9-423c-b3fa-66949ce48ff1"),
    ("Circle of Dreams", "608d4844-820f-4351-a780-f5a65b482e43"),
]


def call(method: str, path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


for name, entity_id in TARGETS:
    proposal = call(
        "POST",
        f"/entities/{entity_id}/metadata-proposals?requester_role=dm",
        {"entity_kind": "worldbuilding", "tags": []},
    )
    approval = call(
        "POST",
        f"/entities/metadata-proposals/{proposal['proposal_id']}/approvals?requester_role=dm",
        {
            "reviewed_version": proposal["version_number"],
            "content_hash": proposal["content_hash"],
            "item_ids": [proposal["item"]["item_id"]],
            "idempotency_key": f"entity-kind-approval:{proposal['proposal_id']}:{proposal['version_number']}",
        },
    )
    receipt = call(
        "POST",
        f"/change-sets/{approval['change_set_id']}/apply",
        {
            "reviewed_version": proposal["version_number"],
            "approval_id": approval["approval_id"],
            "content_hash": proposal["content_hash"],
        },
    )
    print(f"{name}: proposal {proposal['proposal_id'][:8]} "
          f"change_set {approval['change_set_id'][:8]} "
          f"applied={receipt.get('outcome')} items={receipt.get('applied_item_ids')}")
