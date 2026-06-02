"""HTTP regression: reviewer cannot publish own scenario from review."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_http_reviewer_cannot_publish_own_scenario(api_client, fake_db) -> None:
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="rev-self-token"):
        signup = await api_client.post(
            "/auth/signup",
            json={
                "email": "selfrev@luneta.dev",
                "password": "Password123!",
                "nickname": "selfrev",
            },
        )
        assert signup.status_code == 200
        await api_client.post("/auth/verify-email", json={"token": "rev-self-token"})
    await fake_db["users"].update_one(
        {"email_normalized": "selfrev@luneta.dev"},
        {"$set": {"role": "reviewer"}},
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "selfrev@luneta.dev", "password": "Password123!"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    create = await api_client.post(
        "/scenarios",
        json={"title": "Own", "description": "Own scenario"},
        headers=headers,
    )
    assert create.status_code == 200
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "selfrev-cat",
            "label": "Category",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "selfrev-risk",
            "label": "Risk",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    cover = await api_client.post(
        f"/scenarios/{sid}/assets/cover",
        headers=headers,
        files={"file": ("cover.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert cover.status_code == 200
    meta = await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
            "usage_context": {
                "children_age_start": 5,
                "children_age_end": 9,
                "children_count": 12,
                "duration_frequency": "once_a_week",
                "physically_present": "yes",
                "online_present": "no",
                "execution_place_affects_scenario": "yes",
                "special_circumstances": "no",
                "consent_in_place": "yes",
            },
        },
        headers=headers,
    )
    assert meta.status_code == 200
    sub = await api_client.post(f"/scenarios/{sid}/submit-review", headers=headers)
    assert sub.status_code == 200
    start = await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=headers)
    assert start.status_code == 200
    pub = await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=headers)
    assert pub.status_code == 403





