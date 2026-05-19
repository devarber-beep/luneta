"""Tests for the /orgs endpoint."""
import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_db
from app.main import app


def _use_real_mongo() -> bool:
    return os.environ.get("LUNETA_TEST_REAL_DB", "").strip().lower() in ("1", "true", "yes")


@pytest.mark.asyncio
async def test_list_orgs_empty(fake_db):
    async def _get_test_db():
        return fake_db

    app.dependency_overrides[get_db] = _get_test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/orgs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if not _use_real_mongo():
        assert data == []

