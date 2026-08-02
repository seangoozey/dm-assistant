import asyncio
from datetime import UTC, datetime
from uuid import UUID

import httpx

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application import ChangeSetApplicationService
from dm_assistant_core.config import Settings
from dm_assistant_core.domain import (
    ApplyChangeSetCommand,
    ChangeSetReceipt,
    ChangeSetRejectedError,
)

CHANGE_SET_ID = UUID("10000000-0000-0000-0000-000000000001")
APPROVAL_ID = UUID("20000000-0000-0000-0000-000000000001")
RECEIPT_ID = UUID("30000000-0000-0000-0000-000000000001")
ITEM_ID = UUID("40000000-0000-0000-0000-000000000001")
CONTENT_HASH = "a" * 64


class RecordingRepository:
    def __init__(self, *, reject: bool = False) -> None:
        self.command: ApplyChangeSetCommand | None = None
        self.reject = reject

    def apply(self, command: ApplyChangeSetCommand) -> ChangeSetReceipt:
        self.command = command
        if self.reject:
            raise ChangeSetRejectedError("approval does not authorize this proposal version")
        return ChangeSetReceipt(
            receipt_id=RECEIPT_ID,
            change_set_id=command.change_set_id,
            outcome="applied",
            applied_item_ids=(ITEM_ID,),
            issued_at=datetime(2026, 8, 1, tzinfo=UTC),
            idempotent_replay=False,
        )


def settings() -> Settings:
    return Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )


async def post_application(repository: RecordingRepository) -> httpx.Response:
    app = create_app(settings(), ChangeSetApplicationService(repository))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            f"/change-sets/{CHANGE_SET_ID}/apply",
            json={
                "reviewed_version": 2,
                "approval_id": str(APPROVAL_ID),
                "content_hash": CONTENT_HASH,
            },
        )


def test_apply_contract_builds_exact_typed_command() -> None:
    repository = RecordingRepository()

    response = asyncio.run(post_application(repository))

    assert response.status_code == 200
    assert repository.command == ApplyChangeSetCommand(
        change_set_id=CHANGE_SET_ID,
        reviewed_version=2,
        approval_id=APPROVAL_ID,
        content_hash=CONTENT_HASH,
    )
    assert response.json()["receipt_id"] == str(RECEIPT_ID)
    assert response.json()["applied_item_ids"] == [str(ITEM_ID)]
    assert response.json()["idempotent_replay"] is False


def test_apply_contract_rejects_stale_or_unauthorized_request() -> None:
    response = asyncio.run(post_application(RecordingRepository(reject=True)))

    assert response.status_code == 409
    assert response.json() == {
        "detail": "approval does not authorize this proposal version"
    }


def test_apply_contract_rejects_unknown_fields_and_invalid_hash() -> None:
    app = create_app(settings(), ChangeSetApplicationService(RecordingRepository()))

    async def request() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            bad_hash = await client.post(
                f"/change-sets/{CHANGE_SET_ID}/apply",
                json={
                    "reviewed_version": 2,
                    "approval_id": str(APPROVAL_ID),
                    "content_hash": "not-a-hash",
                },
            )
            extra = await client.post(
                f"/change-sets/{CHANGE_SET_ID}/apply",
                json={
                    "reviewed_version": 2,
                    "approval_id": str(APPROVAL_ID),
                    "content_hash": CONTENT_HASH,
                    "approve_all": True,
                },
            )
            return bad_hash, extra

    bad_hash, extra = asyncio.run(request())
    assert bad_hash.status_code == 422
    assert extra.status_code == 422


def test_apply_is_the_only_mutating_http_operation() -> None:
    app = create_app(settings(), ChangeSetApplicationService(RecordingRepository()))
    canonical_mutating_operations = {
        (path, method)
        for path, operations in app.openapi()["paths"].items()
        for method, operation in operations.items()
        if method in {"post", "put", "patch", "delete"}
        and "campaign" in operation.get("tags", [])
    }

    assert canonical_mutating_operations == {("/change-sets/{change_set_id}/apply", "post")}
