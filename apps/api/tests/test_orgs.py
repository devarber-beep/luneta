"""Tests for the /orgs endpoint."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_list_orgs_empty():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/orgs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

