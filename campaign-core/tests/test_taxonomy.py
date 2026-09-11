import asyncio

import httpx
import pytest
from pydantic import ValidationError

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application import (
    CreateCandidateProposalCommand,
    TaxonomyService,
    TaxonomySnapshot,
)
from dm_assistant_core.config import Settings
from dm_assistant_core.domain import (
    ENTITY_KIND_GUIDANCE,
    INITIAL_TAGS,
    EntityKind,
    normalize_tags,
)


class StaticTaxonomyRepository:
    def snapshot(self) -> TaxonomySnapshot:
        return TaxonomySnapshot(
            entity_kinds=ENTITY_KIND_GUIDANCE,
            tags=tuple(sorted(INITIAL_TAGS)),
        )


def settings() -> Settings:
    return Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )


def test_entity_kinds_are_small_and_tags_normalize_case_insensitively() -> None:
    assert {kind.value for kind in EntityKind} == {
        "npc",
        "pc",
        "location",
        "faction",
        "item",
        "event",
        "worldbuilding",
        "rules_element",
    }
    assert normalize_tags((" Deity ", "Political")) == ("deity", "political")
    with pytest.raises(ValueError, match="unique case-insensitively"):
        normalize_tags(("Deity", "deity"))


def test_create_entity_rejects_unsupported_kind_and_duplicate_tags() -> None:
    base = {
        "mutation_kind": "create_entity",
        "candidate_id": "50000000-0000-0000-0000-000000000001",
        "evidence_revision_id": "60000000-0000-0000-0000-000000000001",
        "target_id": "80000000-0000-0000-0000-000000000001",
        "canonical_name": "Sanitized Subject",
    }
    with pytest.raises(ValidationError):
        CreateCandidateProposalCommand.model_validate(
            {"items": [{**base, "entity_kind": "other", "tags": []}]}
        )
    with pytest.raises(ValidationError, match="unique case-insensitively"):
        CreateCandidateProposalCommand.model_validate(
            {"items": [{**base, "entity_kind": "npc", "tags": ["Deity", "deity"]}]}
        )


def test_taxonomy_endpoint_returns_guidance_and_is_dm_only() -> None:
    app = create_app(settings(), taxonomy=TaxonomyService(StaticTaxonomyRepository()))

    async def exercise() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            allowed = await client.get("/taxonomy?requester_role=dm")
            forbidden = await client.get("/taxonomy?requester_role=party")
            return allowed, forbidden

    allowed, forbidden = asyncio.run(exercise())
    assert allowed.status_code == 200
    assert {item["kind"] for item in allowed.json()["entity_kinds"]} == {
        kind.value for kind in EntityKind
    }
    assert allowed.json()["tags"] == sorted(INITIAL_TAGS)
    assert forbidden.status_code == 403
