"""HTTP tests for stripping inactive catalog selections on scenario edit."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from bson import ObjectId


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
async def test_patch_strips_inactive_category_and_ethical_risk(api_client, fake_db) -> None:
    headers = await _signup_investigator(
        api_client, fake_db, email="catalog-strip@luneta.dev", token="cat-strip"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Catalog cleanup", "description": "Draft with stale catalog ids."},
        headers=headers,
    )
    assert create.status_code in (200, 201)
    sid = create.json()["id"]
    now = datetime.now(UTC)
    active_cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "active-cat", "label": "Active", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    inactive_cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "inactive-cat",
            "label": "Inactive",
            "is_active": False,
            "sort_order": 1,
            "created_at": now,
            "updated_at": now,
        }
    )
    active_risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "active-risk", "label": "Active risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    inactive_risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "inactive-risk",
            "label": "Inactive risk",
            "is_active": False,
            "sort_order": 1,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "category_ids": [str(active_cat.inserted_id), str(inactive_cat.inserted_id)],
                "ethical_risk_ids": [str(active_risk.inserted_id), str(inactive_risk.inserted_id)],
            }
        },
    )

    patch = await api_client.patch(
        f"/scenarios/{sid}",
        json={"description": "Touch draft to trigger catalog cleanup."},
        headers=headers,
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["category_ids"] == [str(active_cat.inserted_id)]
    assert body["ethical_risk_ids"] == [str(active_risk.inserted_id)]
