"""HTTP tests for scenario authoring catalog endpoints."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest


async def _signup_investigator(api_client, fake_db, *, email: str, token: str) -> dict[str, str]:
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=token):
        await api_client.post(
            "/auth/signup",
            json={
                "email": email,
                "password": "Password123!",
                "first_name": email.split("@")[0].capitalize(),
                "last_name": "User",
            },
        )
        await api_client.post("/auth/verify-email", json={"token": token})
    await fake_db["users"].update_one({"email_normalized": email}, {"$set": {"role": "investigator"}})
    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_investigator_can_list_active_authoring_catalogs(api_client, fake_db) -> None:
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "author-cat", "label": "Education", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "author-risk", "label": "Privacy", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    headers = await _signup_investigator(
        api_client, fake_db, email="authorcat@luneta.dev", token="author-cat"
    )

    categories = await api_client.get("/catalog/scenario-classification", headers=headers)
    assert categories.status_code == 200
    assert categories.json()["items"] == [{"id": str(cat.inserted_id), "label": "Education"}]

    risks = await api_client.get("/catalog/ethical-risks", headers=headers)
    assert risks.status_code == 200
    assert risks.json()["items"] == [{"id": str(risk.inserted_id), "label": "Privacy"}]

    public_categories = await api_client.get("/public/catalog/categories")
    assert public_categories.status_code == 200
    assert public_categories.json()["items"] == [{"id": str(cat.inserted_id), "label": "Education"}]
