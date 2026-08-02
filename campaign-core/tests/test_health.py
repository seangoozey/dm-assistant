import asyncio

import httpx
import pytest
from pydantic import ValidationError

from dm_assistant_core.api.app import create_app
from dm_assistant_core.config import Settings


def test_health_contract() -> None:
    settings = Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
    )
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app(settings))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "campaign-core",
        "version": "0.1.0",
    }


def test_configured_ui_origin_receives_cors_preflight() -> None:
    settings = Settings(
        database_url="postgresql://campaign:secret@localhost:5432/campaign",
        run_migrations=False,
        cors_origins="http://127.0.0.1:58018",
    )

    async def request_preflight() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app(settings))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.options(
                "/retrieval/query",
                headers={
                    "Origin": "http://127.0.0.1:58018",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

    response = asyncio.run(request_preflight())

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:58018"


def test_cors_origin_rejects_paths() -> None:
    with pytest.raises(ValidationError, match="without a path"):
        Settings(
            database_url="postgresql://campaign:secret@localhost:5432/campaign",
            cors_origins="https://example.test/not-an-origin",
        )
