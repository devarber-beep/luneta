"""Admin catalog CRUD (scenario classification and ethical risks)."""
from __future__ import annotations

import pytest

from tests.user_doc_helpers import user_doc


async def _admin_headers(api_client, fake_db) -> dict[str, str]:
    await fake_db["users"].insert_one(
        user_doc(email="catalogadmin@luneta.dev", role="admin", password_plain="AdminPass123!")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "catalogadmin@luneta.dev", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_classification_crud(api_client, fake_db) -> None:
    headers = await _admin_headers(api_client, fake_db)
    listed = await api_client.get("/admin/catalog/scenario-classification", headers=headers)
    assert listed.status_code == 200

    created = await api_client.post(
        "/admin/catalog/scenario-classification",
        json={"label": "Test category", "sort_order": 99},
        headers=headers,
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]

    patched = await api_client.patch(
        f"/admin/catalog/scenario-classification/{entry_id}",
        json={"label": "Test category updated", "is_active": False},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["label"] == "Test category updated"
    assert patched.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_ethical_risk_crud(api_client, fake_db) -> None:
    headers = await _admin_headers(api_client, fake_db)
    created = await api_client.post(
        "/admin/catalog/ethical-risks",
        json={"label": "Test risk", "sort_order": 1},
        headers=headers,
    )
    assert created.status_code == 201
    entry_id = created.json()["id"]

    listed = await api_client.get("/admin/catalog/ethical-risks", headers=headers)
    assert listed.status_code == 200
    assert any(i["id"] == entry_id for i in listed.json()["items"])

    patched = await api_client.patch(
        f"/admin/catalog/ethical-risks/{entry_id}",
        json={"is_active": False},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False
