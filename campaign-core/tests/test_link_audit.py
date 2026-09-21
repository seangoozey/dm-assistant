"""Standing entity/document link audit (TKT-0110)."""

import asyncio
from uuid import uuid4

import httpx
import pytest

from dm_assistant_core.api.app import create_app
from dm_assistant_core.application.link_audit import LinkAuditService
from dm_assistant_core.config import Settings


class MemoryRepository:
    def __init__(self) -> None:
        self.entities: list[tuple] = []
        self.names: list[str] = []

    def entities_with_sources(self):
        return self.entities

    def all_entity_names(self):
        return self.names


def test_wrong_page_borrow_flagged_when_filename_carries_another_entity() -> None:
    repo = MemoryRepository()
    romulus = uuid4()
    repo.entities.append((
        romulus, "Romulus", "npc",
        [(uuid4(), "lore/the-wrath-of-romulus.md"), (uuid4(), "npcs/romulus.md")],
    ))
    repo.names = ["Romulus", "The Wrath of Romulus"]
    result = LinkAuditService(repo).audit()
    borrows = [f for f in result.findings if f.kind == "wrong_page_borrow"]
    assert len(borrows) == 1
    assert "the-wrath-of-romulus" in (borrows[0].document_path or "")
    assert "The Wrath of Romulus" in borrows[0].detail


def test_exact_match_not_flagged() -> None:
    repo = MemoryRepository()
    repo.entities.append((
        uuid4(), "Ruh", "npc",
        [(uuid4(), "npcs/ruh.md")],
    ))
    repo.names = ["Ruh"]
    result = LinkAuditService(repo).audit()
    assert result.findings == ()


def test_qualifier_suffix_not_flagged() -> None:
    # lore/thanore-history.md is Thanore's page (history is generic).
    repo = MemoryRepository()
    repo.entities.append((
        uuid4(), "Thanore", "location",
        [(uuid4(), "lore/thanore-history.md")],
    ))
    repo.names = ["Thanore"]
    result = LinkAuditService(repo).audit()
    assert result.findings == ()


def test_zero_affinity_when_many_sources_none_match() -> None:
    repo = MemoryRepository()
    repo.entities.append((
        uuid4(), "Ishi'ra'la", "location",
        [(uuid4(), "encounters/floor1.md"), (uuid4(), "encounters/floor2.md"),
         (uuid4(), "encounters/floor3.md"), (uuid4(), "encounters/floor4.md")],
    ))
    repo.names = ["Ishi'ra'la"]
    result = LinkAuditService(repo).audit()
    zero = [f for f in result.findings if f.kind == "zero_affinity"]
    assert len(zero) == 1
    assert "4 claim-evidenced sources" in zero[0].detail


def test_link_audit_api_is_dm_only() -> None:
    service = LinkAuditService(MemoryRepository())
    app = create_app(Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    ), link_audit=service)

    async def requests() -> tuple[httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            forbidden = await client.get("/campaign/link-audit?requester_role=party")
            ok = await client.get("/campaign/link-audit?requester_role=dm")
            return forbidden, ok

    forbidden, ok = asyncio.run(requests())
    assert forbidden.status_code == 403
    assert ok.status_code == 200
    assert ok.json()["findings"] == []
