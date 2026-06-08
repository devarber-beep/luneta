"""HTTP tests for ethical evaluations."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from bson import ObjectId

from tests.scenario_fixtures import COMPLETE_USAGE_CONTEXT


async def _signup_and_promote(api_client, fake_db, *, email: str, role: str, token: str) -> dict:
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=token):
        await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "first_name": email.split("@")[0].capitalize(), "last_name": "User"},
        )
        await api_client.post("/auth/verify-email", json={"token": token})
    await fake_db["users"].update_one({"email_normalized": email}, {"$set": {"role": role}})
    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _publish_scenario(api_client, fake_db, *, owner_h: dict, rev_h: dict) -> tuple[str, str]:
    owner_doc = await fake_db["users"].find_one({"email_normalized": "evowner@luneta.dev"})
    rev_doc = await fake_db["users"].find_one({"email_normalized": "evrev@luneta.dev"})
    owner_id = str(owner_doc["_id"])
    rev_id = str(rev_doc["_id"])
    now = datetime.now(UTC)
    await fake_db["reviewer_assignments"].insert_one(
        {
            "reviewer_user_id": rev_id,
            "investigator_user_id": owner_id,
            "created_at": now,
            "created_by_user_id": rev_id,
        }
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Eval target", "description": "Published body."},
        headers=owner_h,
    )
    sid = create.json()["id"]
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": "ev-cat",
            "label": "Cat",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": "ev-risk",
            "label": "Privacy risk",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": f"scenarios/{sid}/cover/cover-1",
                    "mime_type": "image/png",
                    "order": 0,
                }
            }
        },
    )
    await api_client.patch(
        f"/scenarios/{sid}",
        json={
            "category_ids": [str(cat.inserted_id)],
            "ethical_risk_ids": [str(risk.inserted_id)],
            "usage_context": COMPLETE_USAGE_CONTEXT,
        },
        headers=owner_h,
    )
    await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    pub = await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=rev_h)
    assert pub.status_code == 200
    return sid, str(risk.inserted_id)


@pytest.mark.asyncio
async def test_registered_submits_evaluation_owner_sees_summary(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="evowner@luneta.dev", role="investigator", token="ev-owner-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="evrev@luneta.dev", role="reviewer", token="ev-rev-tok"
    )
    reg_h = await _signup_and_promote(
        api_client, fake_db, email="evreg@luneta.dev", role="registered", token="ev-reg-tok"
    )
    sid, risk_id = await _publish_scenario(api_client, fake_db, owner_h=owner_h, rev_h=rev_h)

    me_before = await api_client.get(f"/scenarios/{sid}/evaluations/me", headers=reg_h)
    assert me_before.status_code == 200
    assert me_before.json()["evaluation"] is None
    assert me_before.json()["can_submit"] is True

    owner_me = await api_client.get(f"/scenarios/{sid}/evaluations/me", headers=owner_h)
    assert owner_me.status_code == 200
    assert owner_me.json()["can_submit"] is False

    submit = await api_client.post(
        f"/scenarios/{sid}/evaluations",
        headers=reg_h,
        json={
            "risk_score": 7.5,
            "benefit_score": 4,
            "detected_ethical_risk_ids": [risk_id],
            "comment": "Needs tighter consent wording.",
        },
    )
    assert submit.status_code == 201
    assert submit.json()["risk_score"] == 7.5

    owner_notifs = await api_client.get("/notifications", headers=owner_h)
    assert owner_notifs.status_code == 200
    eval_notifs = [
        n
        for n in owner_notifs.json()["items"]
        if n["notification_type"] == "scenario_evaluation_received"
    ]
    assert len(eval_notifs) == 1
    assert eval_notifs[0]["scenario_id"] == sid

    dup = await api_client.post(
        f"/scenarios/{sid}/evaluations",
        headers=reg_h,
        json={
            "risk_score": 5,
            "benefit_score": 5,
            "detected_ethical_risk_ids": [risk_id],
            "comment": "",
        },
    )
    assert dup.status_code == 409

    summary = await api_client.get(f"/scenarios/{sid}/evaluations/summary", headers=owner_h)
    assert summary.status_code == 200
    body = summary.json()
    assert body["evaluation_count"] == 1
    assert body["average_risk_score"] == 7.5
    assert body["average_benefit_score"] == 4.0
    assert "Privacy risk" in body["detected_ethical_risk_labels"]
    assert body["comments"] == ["Needs tighter consent wording."]

    reg_summary = await api_client.get(f"/scenarios/{sid}/evaluations/summary", headers=reg_h)
    assert reg_summary.status_code == 200
    reg_body = reg_summary.json()
    assert reg_body["evaluation_count"] == 1
    assert reg_body["average_risk_score"] == 7.5
    assert reg_body["average_benefit_score"] == 4.0
    assert "Privacy risk" in reg_body["detected_ethical_risk_labels"]
    assert reg_body.get("comments", []) == []

    reg_detail = await api_client.get(f"/scenarios/{sid}/evaluations", headers=reg_h)
    assert reg_detail.status_code == 403

    owner_detail = await api_client.get(f"/scenarios/{sid}/evaluations", headers=owner_h)
    assert owner_detail.status_code == 403

    admin_h = await _signup_and_promote(
        api_client, fake_db, email="evadmin@luneta.dev", role="admin", token="ev-admin-tok"
    )
    admin_detail = await api_client.get(f"/scenarios/{sid}/evaluations", headers=admin_h)
    assert admin_detail.status_code == 200
    assert len(admin_detail.json()["items"]) == 1
    assert admin_detail.json()["items"][0]["evaluator_display_name"] is not None
    assert admin_detail.json()["items"][0]["comment"] == "Needs tighter consent wording."

    public_list = await api_client.get("/public/scenarios")
    assert public_list.status_code == 200
    assert "items" in public_list.json()

    admin_h2 = await _signup_and_promote(
        api_client, fake_db, email="evadm2@luneta.dev", role="admin", token="ev-adm2-tok"
    )
    targets = await api_client.get("/admin/evaluations/moderation-targets", headers=admin_h2)
    assert targets.status_code == 200
    row = next((i for i in targets.json()["items"] if i["scenario_id"] == sid), None)
    assert row is not None
    assert row["evaluation_count"] == 1
    assert row["title"]

    forbidden = await api_client.get("/admin/evaluations/moderation-targets", headers=owner_h)
    assert forbidden.status_code == 403
