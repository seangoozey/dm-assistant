from __future__ import annotations

import asyncio
from uuid import UUID

import httpx

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application import (
    CandidateListQuery,
    ImportCandidatePage,
    ImportCandidateReview,
    ImportReviewItemPage,
    ImportReviewService,
    ImportRunDetail,
    ImportRunListQuery,
    ImportRunPage,
    ReviewItemListQuery,
)
from dm_assistant_core.config import Settings
from dm_assistant_core.domain import RequesterVisibility


class RecordingImportReviewRepository:
    def __init__(self) -> None:
        self.run_query: ImportRunListQuery | None = None
        self.candidate_query: CandidateListQuery | None = None
        self.review_query: ReviewItemListQuery | None = None

    def list_runs(self, query: ImportRunListQuery) -> ImportRunPage:
        self.run_query = query
        return ImportRunPage(items=(), total=0, limit=query.limit, offset=query.offset)

    def get_run(self, run_id: UUID) -> ImportRunDetail | None:
        return None

    def list_candidates(self, query: CandidateListQuery) -> ImportCandidatePage:
        self.candidate_query = query
        return ImportCandidatePage(items=(), total=0, limit=query.limit, offset=query.offset)

    def get_candidate(
        self, candidate_id: UUID, requester: RequesterVisibility
    ) -> ImportCandidateReview | None:
        return None

    def list_reviews(self, query: ReviewItemListQuery) -> ImportReviewItemPage:
        self.review_query = query
        return ImportReviewItemPage(items=(), total=0, limit=query.limit, offset=query.offset)


def settings() -> Settings:
    return Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )


async def _get(app: object, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_import_review_routes_are_typed_paginated_and_filterable() -> None:
    repository = RecordingImportReviewRepository()
    app = create_app(settings(), import_reviews=ImportReviewService(repository))

    runs = asyncio.run(_get(app, "/imports/runs?requester_role=dm&limit=20&offset=3"))
    candidates = asyncio.run(
        _get(
            app,
            "/imports/candidates?requester_role=party&classification=durable_evidence"
            "&state=established&source=npcs&limit=10",
        )
    )
    reviews = asyncio.run(
        _get(
            app,
            "/imports/reviews?requester_role=dm&state=possible&authority=brainstorm"
            "&visibility=dm_only&source=gm&limit=5",
        )
    )

    assert runs.status_code == 200
    assert runs.json() == {"items": [], "total": 0, "limit": 20, "offset": 3}
    assert repository.run_query is not None
    assert repository.run_query.requester.role.value == "dm"
    assert candidates.status_code == 200
    assert repository.candidate_query is not None
    assert repository.candidate_query.requester.role.value == "party"
    assert repository.candidate_query.classification.value == "durable_evidence"
    assert repository.candidate_query.state.value == "established"
    assert repository.candidate_query.source == "npcs"
    assert reviews.status_code == 200
    assert repository.review_query is not None
    assert repository.review_query.state.value == "possible"
    assert repository.review_query.authority.value == "brainstorm"
    assert repository.review_query.visibility.value == "dm_only"
    assert repository.review_query.source == "gm"


def test_receipts_and_review_items_are_dm_only() -> None:
    repository = RecordingImportReviewRepository()
    app = create_app(settings(), import_reviews=ImportReviewService(repository))

    runs = asyncio.run(_get(app, "/imports/runs?requester_role=party"))
    reviews = asyncio.run(_get(app, "/imports/reviews?requester_role=character&character_id=pc-1"))

    assert runs.status_code == 403
    assert reviews.status_code == 403
    assert repository.run_query is None
    assert repository.review_query is None


def test_character_identity_and_missing_records_fail_closed() -> None:
    repository = RecordingImportReviewRepository()
    app = create_app(settings(), import_reviews=ImportReviewService(repository))
    missing_id = "10000000-0000-0000-0000-000000000001"

    invalid_requester = asyncio.run(
        _get(app, "/imports/candidates?requester_role=character")
    )
    missing_candidate = asyncio.run(
        _get(app, f"/imports/candidates/{missing_id}?requester_role=dm")
    )
    missing_run = asyncio.run(_get(app, f"/imports/runs/{missing_id}?requester_role=dm"))

    assert invalid_requester.status_code == 422
    assert missing_candidate.status_code == 404
    assert missing_run.status_code == 404
