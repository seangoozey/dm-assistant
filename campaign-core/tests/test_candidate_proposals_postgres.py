from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import psycopg
import pytest

from dm_assistant_core.adapters.postgres.migrate import run_migrations
from dm_assistant_core.api.app import create_app
from dm_assistant_core.config import Settings
from dm_assistant_core.importer import MarkdownScanner, MarkdownScannerConfig

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPOSITORY_ROOT / "tests" / "fixtures" / "markdown_import"
TEST_DSN = os.getenv("CAMPAIGN_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DSN is None,
    reason="set CAMPAIGN_TEST_DATABASE_URL to a disposable PostgreSQL database",
)


@pytest.fixture(autouse=True)
def disposable_database() -> None:
    if TEST_DSN is None:
        return
    database_name = psycopg.conninfo.conninfo_to_dict(TEST_DSN).get("dbname", "")
    if not database_name.endswith("_test"):
        raise RuntimeError("integration tests require a database name ending in _test")
    run_migrations(TEST_DSN)
    with psycopg.connect(TEST_DSN) as connection:
        connection.execute(
            "TRUNCATE TABLE import_runs, source_documents, workflow_sessions, change_sets CASCADE"
        )


def app() -> Any:
    assert TEST_DSN is not None
    return create_app(Settings(database_url=TEST_DSN, environment="test", run_migrations=False))


def test_brainstorm_exact_evidence_pins_persist_without_an_entity() -> None:
    from dm_assistant_core.adapters.postgres.brainstorms import PostgresBrainstormRepository
    from dm_assistant_core.adapters.postgres.database import PostgresDatabase
    from dm_assistant_core.application.brainstorms import StartBrainstormCommand
    from dm_assistant_core.domain import RetrievedEvidence

    assert TEST_DSN is not None
    repository = PostgresBrainstormRepository(PostgresDatabase(TEST_DSN))
    session = repository.start(StartBrainstormCommand(title="Evidence", idempotency_key="pin-test"))
    evidence = RetrievedEvidence(
        record_id=str(uuid4()), assertion="The castle at Tsunadis opposes the cultists.",
        citation="lore/cosmology.md#Titans", state="established",
        authority="explicit_lore", role="support",
    )
    repository.pin_evidence(session.session_id, evidence)
    repository.pin_evidence(session.session_id, evidence)
    resumed = repository.get(session.session_id)
    assert resumed is not None
    assert len(resumed.evidence_pins) == 1
    assert resumed.evidence_pins[0].assertion == evidence.assertion
    assert resumed.evidence_pins[0].entity_id is None
    assert repository.unpin_evidence(session.session_id, evidence.record_id).evidence_pins == ()


def fixture_batch(scan_id: str) -> Any:
    return MarkdownScanner(
        MarkdownScannerConfig(
            root=FIXTURE_ROOT,
            root_identifier="sanitized-proposal-fixture",
            importer_version="markdown-importer/1.0",
            parser_version="markdown-parser/1.0",
            path_policy_version="starfall-path-policy/1.0",
            read_only=True,
            scan_id=scan_id,
        )
    ).scan()


async def import_fixture(client: httpx.AsyncClient, scan_id: str) -> None:
    imported = await client.post(
        "/imports/markdown/scan", json=fixture_batch(scan_id).model_dump(mode="json")
    )
    assert imported.status_code == 200, imported.text


def candidate(
    authority: str, *, conditional: bool | None = None, offset: int = 0
) -> dict[str, Any]:
    assert TEST_DSN is not None
    clauses = ["ic.authority = %s", "NOT ic.evidence_only", "ic.status = 'active'"]
    parameters: list[Any] = [authority]
    if conditional is not None:
        clauses.append("ic.is_conditional = %s")
        parameters.append(conditional)
    parameters.append(offset)
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT ic.id, ice.source_revision_id, ic.state::text, ic.authority::text, "
            "ic.visibility, ic.is_conditional, ic.predicts_subject_action, ic.assertion_text "
            "FROM import_candidates ic JOIN import_candidate_evidence ice "
            "ON ice.candidate_id = ic.id WHERE "
            + " AND ".join(clauses)
            + " ORDER BY ic.id OFFSET %s LIMIT 1",
            tuple(parameters),
        ).fetchone()
    assert row is not None
    return {
        "id": row[0],
        "revision_id": row[1],
        "state": str(row[2]),
        "authority": str(row[3]),
        "visibility": str(row[4]),
        "conditional": bool(row[5]),
        "predicts": bool(row[6]),
        "assertion": str(row[7]),
    }


def entity_item(
    selected: dict[str, Any],
    target_id: UUID,
    name: str,
    entity_kind: str = "npc",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "mutation_kind": "create_entity",
        "candidate_id": str(selected["id"]),
        "evidence_revision_id": str(selected["revision_id"]),
        "target_id": str(target_id),
        "entity_kind": entity_kind,
        "canonical_name": name,
        "tags": tags or [],
    }


def claim_item(
    selected: dict[str, Any],
    target_id: UUID,
    subject_id: UUID,
    predicate: str,
    *,
    state: str | None = None,
    authority: str | None = None,
    observed_at: dict[str, Any] | None = None,
    effective_from: dict[str, Any] | None = None,
    expected_at: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "mutation_kind": "create_claim",
        "candidate_id": str(selected["id"]),
        "evidence_revision_id": str(selected["revision_id"]),
        "target_id": str(target_id),
        "subject_entity_id": str(subject_id),
        "predicate": predicate,
        "state": state or selected["state"],
        "authority": authority or selected["authority"],
        "visibility": selected["visibility"],
        "confidence": "1",
        "is_conditional": selected["conditional"],
        "predicts_subject_action": selected["predicts"],
        "recorded_at": "2026-08-01T12:00:00Z",
        "observed_at": observed_at,
        "effective_from": effective_from,
        "expected_at": expected_at,
    }


async def approve_and_apply(
    client: httpx.AsyncClient,
    proposal: dict[str, Any],
    item_ids: list[str],
    key: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    approved = await client.post(
        f"/imports/proposals/{proposal['proposal_id']}/approvals?requester_role=dm",
        json={
            "reviewed_version": proposal["version_number"],
            "content_hash": proposal["content_hash"],
            "item_ids": item_ids,
            "idempotency_key": key,
        },
    )
    assert approved.status_code == 200, approved.text
    approval = approved.json()
    applied = await client.post(
        f"/change-sets/{approval['change_set_id']}/apply",
        json={
            "reviewed_version": proposal["version_number"],
            "approval_id": approval["approval_id"],
            "content_hash": proposal["content_hash"],
        },
    )
    assert applied.status_code == 200, applied.text
    return approval, applied.json()


def test_exact_scopes_apply_candidate_evidence_and_status_transactionally() -> None:
    assert TEST_DSN is not None
    application = app()

    async def exercise() -> tuple[dict[str, Any], UUID, UUID, str]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await import_fixture(client, "candidate-proposal-apply")
            selected = candidate("explicit_lore")
            entity_id, claim_id = uuid4(), uuid4()
            created = await client.post(
                "/imports/proposals?requester_role=dm",
                json={
                    "items": [
                        entity_item(
                            selected,
                            entity_id,
                            "Sanitized Archivist",
                            tags=["Deity"],
                        ),
                        claim_item(selected, claim_id, entity_id, "documented_fact"),
                    ]
                },
            )
            assert created.status_code == 200, created.text
            proposal = created.json()
            entity_item_id = proposal["items"][0]["item_id"]
            claim_item_id = proposal["items"][1]["item_id"]
            _, first_apply = await approve_and_apply(
                client, proposal, [entity_item_id], "proposal-scope-entity"
            )
            assert first_apply["applied_item_ids"] == [entity_item_id]
            with psycopg.connect(TEST_DSN) as connection:
                mid_state = connection.execute(
                    "SELECT review_status FROM import_candidates WHERE id = %s",
                    (selected["id"],),
                ).fetchone()
                assert mid_state == ("proposed",)
            _, second_apply = await approve_and_apply(
                client, proposal, [claim_item_id], "proposal-scope-claim"
            )
            assert second_apply["applied_item_ids"] == [claim_item_id]
            return proposal, entity_id, claim_id, selected["assertion"]

    proposal, entity_id, claim_id, assertion = asyncio.run(exercise())
    with psycopg.connect(TEST_DSN) as connection:
        entity = connection.execute(
            "SELECT e.canonical_name, e.entity_type, kd.canonical_key "
            "FROM entities e JOIN records r ON r.id = e.id "
            "JOIN kind_definitions kd ON kd.id = r.record_type_kind_id "
            "WHERE e.id = %s",
            (entity_id,),
        ).fetchone()
        tags = connection.execute(
            "SELECT normalized_name FROM current_entity_tags WHERE entity_id = %s",
            (entity_id,),
        ).fetchall()
        claim = connection.execute(
            "SELECT assertion_text, state::text, authority::text FROM claims WHERE id = %s",
            (claim_id,),
        ).fetchone()
        evidence = connection.execute(
            "SELECT count(*) FROM claim_evidence WHERE claim_id = %s", (claim_id,)
        ).fetchone()
        status = connection.execute(
            "SELECT p.status::text, ic.review_status FROM proposals p "
            "JOIN proposal_versions pv ON pv.proposal_id = p.id "
            "JOIN proposal_items pi ON pi.proposal_version_id = pv.id "
            "JOIN proposal_candidate_bindings pcb ON pcb.proposal_item_id = pi.id "
            "JOIN import_candidates ic ON ic.id = pcb.candidate_id "
            "WHERE p.id = %s LIMIT 1",
            (proposal["proposal_id"],),
        ).fetchone()
    assert entity == ("Sanitized Archivist", "npc", "entity")
    assert tags == [("deity",)]
    assert claim == (assertion, "established", "explicit_lore")
    assert evidence == (1,)
    assert status == ("applied", "applied")


def test_revision_invalidates_prior_unapplied_approval() -> None:
    assert TEST_DSN is not None
    application = app()

    async def exercise() -> tuple[httpx.Response, UUID, UUID]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await import_fixture(client, "candidate-proposal-revision")
            selected = candidate("explicit_lore")
            first_target, second_target = uuid4(), uuid4()
            created = await client.post(
                "/imports/proposals?requester_role=dm",
                json={"items": [entity_item(selected, first_target, "Sanitized First Draft")]},
            )
            proposal = created.json()
            approved = await client.post(
                f"/imports/proposals/{proposal['proposal_id']}/approvals?requester_role=dm",
                json={
                    "reviewed_version": 1,
                    "content_hash": proposal["content_hash"],
                    "item_ids": [proposal["items"][0]["item_id"]],
                    "idempotency_key": "stale-version",
                },
            )
            assert approved.status_code == 200
            revised = await client.post(
                f"/imports/proposals/{proposal['proposal_id']}/versions?requester_role=dm",
                json={"items": [entity_item(selected, second_target, "Sanitized Revised Draft")]},
            )
            assert revised.status_code == 200
            stale = await client.post(
                f"/change-sets/{approved.json()['change_set_id']}/apply",
                json={
                    "reviewed_version": 1,
                    "approval_id": approved.json()["approval_id"],
                    "content_hash": proposal["content_hash"],
                },
            )
            return stale, first_target, UUID(approved.json()["approval_id"])

    stale, first_target, approval_id = asyncio.run(exercise())
    assert stale.status_code == 409
    with psycopg.connect(TEST_DSN) as connection:
        entity = connection.execute(
            "SELECT 1 FROM entities WHERE id = %s", (first_target,)
        ).fetchone()
        revoked = connection.execute(
            "SELECT revoked_at IS NOT NULL FROM approvals WHERE id = %s", (approval_id,)
        ).fetchone()
    assert entity is None
    assert revoked == (True,)


def test_dispositions_do_not_mutate_canon_and_safety_rules_fail_closed() -> None:
    assert TEST_DSN is not None
    application = app()

    async def exercise() -> tuple[httpx.Response, httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await import_fixture(client, "candidate-proposal-safety")
            deferred_candidate = candidate("explicit_lore", offset=0)
            rejected_candidate = candidate("explicit_lore", offset=1)
            deferred = await client.post(
                f"/imports/candidates/{deferred_candidate['id']}/disposition?requester_role=dm",
                json={"disposition": "deferred", "reason": "Identity is not resolved"},
            )
            rejected = await client.post(
                f"/imports/candidates/{rejected_candidate['id']}/disposition?requester_role=dm",
                json={"disposition": "rejected", "reason": "Not campaign truth"},
            )
            assert deferred.status_code == 200
            assert rejected.status_code == 200

            planning = candidate("preparation", conditional=False)
            planning_as_lore = await client.post(
                "/imports/proposals?requester_role=dm",
                json={
                    "items": [
                        claim_item(
                            planning,
                            uuid4(),
                            uuid4(),
                            "future_choice",
                            state="established",
                            authority="explicit_lore",
                        )
                    ]
                },
            )
            brainstorm = candidate("brainstorm")
            brainstorm_as_lore = await client.post(
                "/imports/proposals?requester_role=dm",
                json={
                    "items": [
                        claim_item(
                            brainstorm,
                            uuid4(),
                            uuid4(),
                            "unapproved_idea",
                            state="established",
                            authority="explicit_lore",
                        )
                    ]
                },
            )
            observed = candidate("real_play")
            observation_without_time = await client.post(
                "/imports/proposals?requester_role=dm",
                json={"items": [claim_item(observed, uuid4(), uuid4(), "occurred_without_time")]},
            )
            return planning_as_lore, brainstorm_as_lore, observation_without_time, deferred

    planning_as_lore, brainstorm_as_lore, observation_without_time, _ = asyncio.run(exercise())
    assert planning_as_lore.status_code == 409
    assert brainstorm_as_lore.status_code == 409
    assert observation_without_time.status_code == 409
    with psycopg.connect(TEST_DSN) as connection:
        counts = connection.execute(
            "SELECT (SELECT count(*) FROM entities), (SELECT count(*) FROM claims), "
            "(SELECT count(*) FROM candidate_dispositions)"
        ).fetchone()
    assert counts == (0, 0, 2)


def test_unbound_source_removed_candidate_can_be_dispositioned_idempotently() -> None:
    assert TEST_DSN is not None
    application = app()

    async def exercise() -> tuple[httpx.Response, httpx.Response, str]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await import_fixture(client, "source-removed-disposition")
            selected = candidate("explicit_lore", offset=0)
            with psycopg.connect(TEST_DSN) as connection:
                connection.execute(
                    "UPDATE import_candidates SET status = 'source_removed' WHERE id = %s",
                    (selected["id"],),
                )
            body = {
                "disposition": "rejected",
                "reason": "Superseded parser output",
            }
            first = await client.post(
                f"/imports/candidates/{selected['id']}/disposition?requester_role=dm",
                json=body,
            )
            replay = await client.post(
                f"/imports/candidates/{selected['id']}/disposition?requester_role=dm",
                json=body,
            )
            return first, replay, str(selected["id"])

    first, replay, candidate_id = asyncio.run(exercise())
    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["disposition_id"] == first.json()["disposition_id"]
    with psycopg.connect(TEST_DSN) as connection:
        row = connection.execute(
            "SELECT review_status, "
            "(SELECT count(*) FROM candidate_dispositions WHERE candidate_id = %s) "
            "FROM import_candidates WHERE id = %s",
            (candidate_id, candidate_id),
        ).fetchone()
    assert row == ("rejected", 1)


def test_pc_agency_and_possible_retcon_conflicts_stop_before_proposal_creation() -> None:
    assert TEST_DSN is not None
    application = app()

    async def exercise() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await import_fixture(client, "candidate-proposal-conflicts")
            lore = candidate("explicit_lore")
            pc_id, established_claim_id = uuid4(), uuid4()
            created = await client.post(
                "/imports/proposals?requester_role=dm",
                json={
                    "items": [
                        entity_item(lore, pc_id, "Sanitized Player Character", "pc"),
                        claim_item(
                            lore,
                            established_claim_id,
                            pc_id,
                            "campaign_status",
                        ),
                    ]
                },
            )
            assert created.status_code == 200, created.text
            proposal = created.json()
            await approve_and_apply(
                client,
                proposal,
                [item["item_id"] for item in proposal["items"]],
                "seed-pc-and-fact",
            )

            planning = candidate("preparation", conditional=False)
            pc_plan = await client.post(
                "/imports/proposals?requester_role=dm",
                json={"items": [claim_item(planning, uuid4(), pc_id, "future_player_choice")]},
            )
            future_lore = candidate("explicit_lore", offset=1)
            future_fact = await client.post(
                "/imports/proposals?requester_role=dm",
                json={
                    "items": [
                        claim_item(
                            future_lore,
                            uuid4(),
                            pc_id,
                            "future_fact",
                            effective_from={"year": 2027, "month": 8, "day": 2},
                        )
                    ]
                },
            )
            observation = candidate("real_play")
            observed_status = claim_item(
                observation,
                uuid4(),
                pc_id,
                "campaign_status",
                observed_at={"year": 2026, "month": 8, "day": 1},
            )
            observed_status["assertion_text"] = lore["assertion"]
            possible_retcon = await client.post(
                "/imports/proposals?requester_role=dm",
                json={"items": [observed_status]},
            )
            return pc_plan, future_fact, possible_retcon

    pc_plan, future_fact, possible_retcon = asyncio.run(exercise())
    assert pc_plan.status_code == 200
    assert future_fact.status_code == 409
    assert "future facts" in future_fact.text
    assert possible_retcon.status_code == 409
    assert "conflict review" in possible_retcon.text
    with psycopg.connect(TEST_DSN) as connection:
        canonical_counts = connection.execute(
            "SELECT (SELECT count(*) FROM entities), (SELECT count(*) FROM claims)"
        ).fetchone()
    assert canonical_counts == (1, 1)


def test_brainstorm_session_can_prepare_but_not_apply_a_strengthened_claim() -> None:
    assert TEST_DSN is not None
    application = app()

    async def exercise() -> tuple[dict[str, Any], UUID]:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await import_fixture(client, "brainstorm-promotion")
            lore = candidate("explicit_lore")
            entity_id = uuid4()
            created = await client.post(
                "/imports/proposals?requester_role=dm",
                json={"items": [entity_item(lore, entity_id, "Sanitized Brainstorm Subject")]},
            )
            assert created.status_code == 200, created.text
            seeded = created.json()
            await approve_and_apply(
                client,
                seeded,
                [item["item_id"] for item in seeded["items"]],
                "seed-brainstorm-subject",
            )

            started = await client.post(
                "/brainstorms?requester_role=dm",
                json={"title": "Sanitized possibility", "idempotency_key": "brainstorm:start"},
            )
            assert started.status_code == 200, started.text
            session = started.json()
            pinned = await client.put(
                f"/brainstorms/{session['session_id']}/pins/{entity_id}?requester_role=dm"
            )
            assert pinned.status_code == 200, pinned.text
            assert pinned.json()["pins"][0]["entity_id"] == str(entity_id)
            thought_text = (
                "Could @Sanitized Brainstorm Subject become the keeper of the northern archive?"
            )
            captured = await client.post(
                f"/brainstorms/{session['session_id']}/thoughts?requester_role=dm",
                json={
                    "text": thought_text,
                    "idempotency_key": "brainstorm:thought:1",
                    "mentions": [
                        {
                            "entity_id": str(entity_id),
                            "display_name": "Sanitized Brainstorm Subject",
                            "start_offset": 6,
                            "end_offset": 35,
                        }
                    ],
                },
            )
            assert captured.status_code == 200, captured.text
            thought = captured.json()["thoughts"][0]
            assert thought["text"] == thought_text
            assert thought["mentions"][0]["entity_id"] == str(entity_id)
            resumed = await client.get("/brainstorms/open?requester_role=dm")
            assert resumed.status_code == 200, resumed.text
            assert resumed.json()["pins"][0]["entity_id"] == str(entity_id)
            assert resumed.json()["thoughts"][0]["mentions"] == thought["mentions"]
            promotion = await client.post(
                "/imports/proposals?requester_role=dm",
                json={
                    "workflow_session_id": session["session_id"],
                    "items": [
                        {
                            "mutation_kind": "create_claim",
                            "candidate_id": thought["candidate_id"],
                            "evidence_revision_id": thought["source_revision_id"],
                            "target_id": str(uuid4()),
                            "subject_entity_id": str(entity_id),
                            "assertion_text": "The subject is keeper of the northern archive.",
                            "state": "established",
                            "authority": "explicit_lore",
                            "visibility": "dm_only",
                            "confidence": "1",
                            "is_conditional": False,
                            "predicts_subject_action": False,
                            "recorded_at": "2026-08-30T12:00:00Z",
                        }
                    ],
                },
            )
            assert promotion.status_code == 200, promotion.text
            return promotion.json(), entity_id

    proposal, entity_id = asyncio.run(exercise())
    assert proposal["status"] == "pending"
    with psycopg.connect(TEST_DSN) as connection:
        claim_count = connection.execute(
            "SELECT count(*) FROM claims WHERE subject_entity_id = %s", (entity_id,)
        ).fetchone()
    assert claim_count == (0,)
