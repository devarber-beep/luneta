"""HTTP tests for sensitive-data check and similarity assistance."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from bson import ObjectId


async def _signup_investigator(api_client, fake_db, *, email: str, token: str) -> dict[str, str]:
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=token):
        await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "first_name": email.split("@")[0].capitalize(), "last_name": "User"},
        )
        await api_client.post("/auth/verify-email", json={"token": token})
    await fake_db["users"].update_one({"email_normalized": email}, {"$set": {"role": "investigator"}})
    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_submit_review_blocked_by_sensitive_email(api_client, fake_db) -> None:
    headers = await _signup_investigator(
        api_client, fake_db, email="sensitive1@luneta.dev", token="sens-1"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    assert create.status_code in (200, 201)
    sid = create.json()["id"]
    now = datetime.now(UTC)
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {"slug": "ai-cat", "label": "Cat", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {"slug": "ai-risk", "label": "Risk", "is_active": True, "sort_order": 0, "created_at": now, "updated_at": now}
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "cover_image": {"asset_id": "c1", "storage_key": f"s/{sid}/c1", "mime_type": "image/png", "order": 0},
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
                "description": "Reach the teacher at teacher@school.edu for details.",
            }
        },
    )
    submit = await api_client.post(f"/scenarios/{sid}/submit-review", headers=headers)
    assert submit.status_code == 400
    detail = submit.json()["detail"]
    msg = detail["message"] if isinstance(detail, dict) else detail
    assert "sensitive" in msg.lower()

    patch = await api_client.patch(
        f"/scenarios/{sid}",
        json={"description": "Still has teacher@school.edu in text."},
        headers=headers,
    )
    assert patch.status_code == 400
    patch_detail = patch.json()["detail"]
    patch_msg = patch_detail["message"] if isinstance(patch_detail, dict) else patch_detail
    assert "sensitive" in patch_msg.lower() or "identifiable" in patch_msg.lower()
    audit = await fake_db["audit_events"].find_one({"action_type": "sensitive_data_check_run"})
    assert audit is not None
    assert audit["current"]["passed"] is False
    assert audit["current"]["action"] == "submit_review"
    assert "email" in audit["current"]["finding_types"]
    assert not any(
        row.get("action_type") == "sensitive_data_check_run"
        and row.get("current", {}).get("action") == "save"
        for row in fake_db["audit_events"]._docs
    )


@pytest.mark.asyncio
async def test_create_draft_runs_similarity_check(api_client, fake_db) -> None:
    headers = await _signup_investigator(
        api_client, fake_db, email="similar-create@luneta.dev", token="sim-create"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "New classroom study", "description": "Observation research with students."},
        headers=headers,
    )
    assert create.status_code in (200, 201)
    sid = create.json()["id"]
    audit = await fake_db["audit_events"].find_one(
        {"action_type": "scenario_similarity_check_run", "subject_id": sid}
    )
    assert audit is not None
    assert "provider" in audit["current"]


@pytest.mark.asyncio
async def test_patch_returns_similarity_advisory_without_blocking_save(api_client, fake_db) -> None:
    headers = await _signup_investigator(
        api_client, fake_db, email="similar-patch@luneta.dev", token="sim-patch"
    )
    author_id = str((await fake_db["users"].find_one({"email_normalized": "similar-patch@luneta.dev"}))["_id"])
    now = datetime.now(UTC)
    await fake_db["scenarios"].insert_one(
        {
            "_id": ObjectId(),
            "slug": "published-base-patch",
            "title": "Classroom smart glasses pilot",
            "description": "Students wear smart glasses during lessons for observation research.",
            "public_title": "Classroom smart glasses pilot",
            "public_description": "Students wear smart glasses during lessons for observation research.",
            "public_slug": "classroom-smart-glasses-patch",
            "author_user_id": author_id,
            "collaborators": [],
            "state": "published",
            "category_ids": [],
            "ethical_risk_ids": [],
            "keywords_normalized": [],
            "published_at": now,
            "last_state_changed_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    create = await api_client.post(
        "/scenarios",
        json={
            "title": "Classroom smart glasses pilot copy",
            "description": "Students wear smart glasses during lessons for observation research in class.",
        },
        headers=headers,
    )
    assert create.status_code in (200, 201)
    body = create.json()
    assert body.get("similarity_advisory") is not None
    assert len(body["similarity_advisory"]["candidates"]) >= 1

    sid = body["id"]
    patch = await api_client.patch(
        f"/scenarios/{sid}",
        json={"summary": "Still similar after save."},
        headers=headers,
    )
    assert patch.status_code == 200
    patch_body = patch.json()
    assert patch_body.get("similarity_advisory") is not None
    assert len(patch_body["similarity_advisory"]["candidates"]) >= 1


@pytest.mark.asyncio
async def test_create_returns_empty_similarity_advisory_for_unrelated_content(api_client, fake_db) -> None:
    headers = await _signup_investigator(
        api_client, fake_db, email="similar2@luneta.dev", token="sim-2"
    )
    author_id = str((await fake_db["users"].find_one({"email_normalized": "similar2@luneta.dev"}))["_id"])
    now = datetime.now(UTC)
    await fake_db["scenarios"].insert_one(
        {
            "_id": ObjectId(),
            "slug": "published-generic",
            "title": "Ethics workshop with children",
            "description": "Students participate in classroom activities during lessons for educational research.",
            "public_title": "Ethics workshop with children",
            "public_description": "Students participate in classroom activities during lessons for educational research.",
            "public_slug": "ethics-workshop",
            "author_user_id": author_id,
            "collaborators": [],
            "state": "published",
            "category_ids": [],
            "ethical_risk_ids": [],
            "keywords_normalized": [],
            "published_at": now,
            "last_state_changed_at": now,
            "created_at": now,
            "updated_at": now,
        }
    )
    create = await api_client.post(
        "/scenarios",
        headers=headers,
        json={
            "title": "Smart glasses field study",
            "description": "Children wear devices while teachers observe learning outcomes in another school.",
        },
    )
    assert create.status_code in (200, 201)
    advisory = create.json().get("similarity_advisory")
    assert advisory is not None
    assert advisory["candidates"] == []



