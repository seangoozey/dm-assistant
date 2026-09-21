import asyncio
from unittest.mock import MagicMock

import httpx

from dm_assistant_core.adapters.memory import InMemoryRetrievalRepository
from dm_assistant_core.adapters.postgres.retrieval import PostgresRetrievalRepository
from dm_assistant_core.api.app import create_app
from dm_assistant_core.application import RetrievalService
from dm_assistant_core.config import Settings
from dm_assistant_core.domain.retrieval import RetrievalPolicy, RetrievalQuery
from tests.test_evidence_comparison import coordinate, record


def test_entire_policy_result_is_unchanged_by_hidden_records():
    policy = RetrievalPolicy()
    for role, character in (("party", None), ("character", "pc")):
        query = RetrievalQuery(question="Where?", requester_visibility={
            "role": role, "character_id": character,
        })
        for public in ((), (record(),), (record(), record("b"))):
            hidden = record("secret", visibility="character:other")
            assert policy.evaluate(query, public) == policy.evaluate(
                query, (*public, hidden), comparison_coordinates=(coordinate("secret"),),
            )


def test_hidden_rows_cannot_crowd_visible_result_out_of_limit(monkeypatch):
    database = MagicMock()
    connection = database.connection.return_value.__enter__.return_value
    hidden = [record(str(index), visibility="dm", citation=f"a/{index}") for index in range(150)]
    public = record("visible", citation="z/visible")
    rows = [(item, *([None] * 20), item.assertion) for item in (*hidden, public)]
    connection.execute.return_value.fetchall.side_effect = [rows, [], []]
    repository = PostgresRetrievalRepository(database)
    monkeypatch.setattr(repository, "_to_record", lambda row: row[0])
    query = RetrievalQuery(question="assertion", requester_visibility={"role": "party"})
    assert repository.relevant_records(query) == (public,)


def test_api_exposes_conflict_contract_and_hides_private_presence():
    settings = Settings(database_url="postgresql://unused:unused@localhost/unused",
                        run_migrations=False)

    async def response(records):
        app = create_app(settings, retrieval=RetrievalService(InMemoryRetrievalRepository(records)))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://test") as client:
            result = await client.post("/retrieval/query", json={
                "question": "Tell me about this person", "requester_visibility": {"role": "party"},
            })
        assert result.status_code == 200
        return result.json()

    visible = (
        record(assertion="This person died at the gates.", state="observed",
               authority="real_play", effective_from="505-11-05"),
        record("b", assertion="This person greets visitors today.",
               effective_from="505-11-11"),
    )
    ordinary = asyncio.run(response(visible))
    assert ordinary == asyncio.run(response((*visible, record("secret", visibility="dm"))))
    issue, = ordinary["conflicts"]
    assert issue["policy_version"] == "verified-death-temporal-v1"
    assert issue["verification"] == "verified_comparison"
    assert {item["record_id"] for item in issue["evidence"]} == {"a", "b"}
    assert issue["requires_review"] is True
    assert ordinary["comparison_coverage"] == "partial"
