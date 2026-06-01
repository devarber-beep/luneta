"""HTTP tests: each notification trigger creates the expected in-app row."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from bson import ObjectId

from tests.user_doc_helpers import user_doc


async def _signup_and_promote(api_client, fake_db, *, email: str, role: str, token: str) -> dict:
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=token):
        await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "nickname": email.split("@")[0]},
        )
        await api_client.post("/auth/verify-email", json={"token": token})
    await fake_db["users"].update_one({"email_normalized": email}, {"$set": {"role": role}})
    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _admin_headers(api_client, fake_db) -> dict:
    await fake_db["users"].insert_one(
        user_doc(email="notif-admin@luneta.dev", role="admin", password_plain="AdminPass123!")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "notif-admin@luneta.dev", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _user_id(fake_db, email: str) -> str:
    doc = await fake_db["users"].find_one({"email_normalized": email})
    assert doc is not None
    return str(doc["_id"])


async def _notifs_of_type(api_client, headers: dict, notification_type: str) -> list[dict]:
    listed = await api_client.get("/notifications", headers=headers)
    assert listed.status_code == 200
    return [row for row in listed.json()["items"] if row["notification_type"] == notification_type]


async def _prepare_in_review(
    api_client,
    fake_db,
    *,
    owner_email: str,
    reviewer_email: str,
    owner_h: dict,
    rev_h: dict,
    title: str = "Notif scenario",
) -> str:
    owner_id = await _user_id(fake_db, owner_email)
    rev_id = await _user_id(fake_db, reviewer_email)
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
        json={"title": title, "description": "Body paragraph one.\n\nParagraph two."},
        headers=owner_h,
    )
    assert create.status_code == 200
    sid = create.json()["id"]
    cat = await fake_db["scenario_classification_catalog"].insert_one(
        {
            "slug": f"notif-cat-{sid[:6]}",
            "label": "Cat",
            "is_active": True,
            "sort_order": 0,
            "created_at": now,
            "updated_at": now,
        }
    )
    risk = await fake_db["ethical_risk_catalog"].insert_one(
        {
            "slug": f"notif-risk-{sid[:6]}",
            "label": "Risk",
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
        json={"category_ids": [str(cat.inserted_id)], "ethical_risk_ids": [str(risk.inserted_id)]},
        headers=owner_h,
    )
    submit = await api_client.post(f"/scenarios/{sid}/submit-review", headers=owner_h)
    assert submit.status_code == 200
    start = await api_client.post(f"/workflow/scenarios/{sid}/start-review", headers=rev_h)
    assert start.status_code == 200
    return sid


@pytest.mark.asyncio
async def test_notification_suggestion_received_accepted_rejected(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="notif-own@luneta.dev", role="investigator", token="notif-own-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="notif-rev@luneta.dev", role="reviewer", token="notif-rev-tok"
    )
    sid = await _prepare_in_review(
        api_client,
        fake_db,
        owner_email="notif-own@luneta.dev",
        reviewer_email="notif-rev@luneta.dev",
        owner_h=owner_h,
        rev_h=rev_h,
        title="Suggestion notif",
    )
    sug = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={
            "scope": "paragraph",
            "kind": "comment",
            "paragraph_index": 0,
            "body": "Consider rephrasing.",
        },
    )
    assert sug.status_code == 201
    sug_id = sug.json()["id"]

    received = await _notifs_of_type(api_client, owner_h, "suggestion_received")
    assert len(received) == 1
    assert received[0]["entity_id"] == sug_id

    accept = await api_client.post(
        f"/scenarios/{sid}/suggestions/{sug_id}/accept",
        headers=owner_h,
    )
    assert accept.status_code == 200
    accepted = await _notifs_of_type(api_client, rev_h, "suggestion_accepted")
    assert len(accepted) == 1

    sug2 = await api_client.post(
        f"/scenarios/{sid}/suggestions",
        headers=rev_h,
        json={"scope": "paragraph", "kind": "comment", "paragraph_index": 1, "body": "Second note."},
    )
    assert sug2.status_code == 201
    reject = await api_client.post(
        f"/scenarios/{sid}/suggestions/{sug2.json()['id']}/reject",
        headers=owner_h,
    )
    assert reject.status_code == 200
    rejected = await _notifs_of_type(api_client, rev_h, "suggestion_rejected")
    assert len(rejected) == 1


@pytest.mark.asyncio
async def test_notification_scenario_submitted_for_review(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="notif-own2@luneta.dev", role="investigator", token="notif-own2-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="notif-rev2@luneta.dev", role="reviewer", token="notif-rev2-tok"
    )
    await _prepare_in_review(
        api_client,
        fake_db,
        owner_email="notif-own2@luneta.dev",
        reviewer_email="notif-rev2@luneta.dev",
        owner_h=owner_h,
        rev_h=rev_h,
    )
    submitted = await _notifs_of_type(api_client, rev_h, "scenario_submitted_for_review")
    assert len(submitted) == 1


@pytest.mark.asyncio
async def test_notification_workflow_published(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="notif-own3@luneta.dev", role="investigator", token="notif-own3-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="notif-rev3@luneta.dev", role="reviewer", token="notif-rev3-tok"
    )
    sid = await _prepare_in_review(
        api_client,
        fake_db,
        owner_email="notif-own3@luneta.dev",
        reviewer_email="notif-rev3@luneta.dev",
        owner_h=owner_h,
        rev_h=rev_h,
        title="Workflow publish notif",
    )
    pub = await api_client.post(f"/workflow/scenarios/{sid}/publish", headers=rev_h)
    assert pub.status_code == 200
    published = await _notifs_of_type(api_client, owner_h, "scenario_review_published")
    assert len(published) == 1


@pytest.mark.asyncio
async def test_notification_workflow_changes_required(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="notif-own3b@luneta.dev", role="investigator", token="notif-own3b-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="notif-rev3b@luneta.dev", role="reviewer", token="notif-rev3b-tok"
    )
    sid = await _prepare_in_review(
        api_client,
        fake_db,
        owner_email="notif-own3b@luneta.dev",
        reviewer_email="notif-rev3b@luneta.dev",
        owner_h=owner_h,
        rev_h=rev_h,
        title="Changes required notif",
    )
    changes = await api_client.post(
        f"/workflow/scenarios/{sid}/request-changes",
        headers=rev_h,
        json={"note": "Please expand the ethics section."},
    )
    assert changes.status_code == 200
    required = await _notifs_of_type(api_client, owner_h, "scenario_review_changes_required")
    assert len(required) == 1
    assert "ethics" in (required[0]["message"] or "").lower()


@pytest.mark.asyncio
async def test_notification_workflow_not_suitable_and_reopen(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="notif-own3c@luneta.dev", role="investigator", token="notif-own3c-tok"
    )
    rev_h = await _signup_and_promote(
        api_client, fake_db, email="notif-rev3c@luneta.dev", role="reviewer", token="notif-rev3c-tok"
    )
    admin_h = await _admin_headers(api_client, fake_db)
    sid = await _prepare_in_review(
        api_client,
        fake_db,
        owner_email="notif-own3c@luneta.dev",
        reviewer_email="notif-rev3c@luneta.dev",
        owner_h=owner_h,
        rev_h=rev_h,
        title="Not suitable notif",
    )
    ns = await api_client.post(
        f"/workflow/scenarios/{sid}/mark-not-suitable",
        headers=rev_h,
        json={"reason": "Does not meet inclusion criteria."},
    )
    assert ns.status_code == 200
    not_suitable = await _notifs_of_type(api_client, owner_h, "scenario_review_not_suitable")
    assert len(not_suitable) == 1

    reopen = await api_client.post(f"/workflow/scenarios/{sid}/reopen", headers=admin_h)
    assert reopen.status_code == 200
    reopened = await _notifs_of_type(api_client, owner_h, "scenario_reopened")
    assert len(reopened) == 1


@pytest.mark.asyncio
async def test_notification_collaborator_added(api_client, fake_db) -> None:
    owner_h = await _signup_and_promote(
        api_client, fake_db, email="notif-own4@luneta.dev", role="investigator", token="notif-own4-tok"
    )
    collab_h = await _signup_and_promote(
        api_client, fake_db, email="notif-col@luneta.dev", role="investigator", token="notif-col-tok"
    )
    collab_id = await _user_id(fake_db, "notif-col@luneta.dev")
    create = await api_client.post(
        "/scenarios",
        json={"title": "Collab notif", "description": "Draft body."},
        headers=owner_h,
    )
    assert create.status_code == 200
    sid = create.json()["id"]
    added = await api_client.post(
        f"/scenarios/{sid}/collaborators",
        headers=owner_h,
        json={"user_id": collab_id},
    )
    assert added.status_code == 200
    rows = await _notifs_of_type(api_client, collab_h, "collaborator_added")
    assert len(rows) == 1
    assert rows[0]["scenario_id"] == sid


@pytest.mark.asyncio
async def test_notification_investigator_invited(api_client, fake_db) -> None:
    admin_h = await _admin_headers(api_client, fake_db)
    with patch("app.services.admin_user_service.secrets.token_urlsafe", return_value="fixed-invite-pass"):
        created = await api_client.post(
            "/admin/users/investigators",
            json={"email": "notif-inv@luneta.dev", "nickname": "notifinv"},
            headers=admin_h,
        )
    assert created.status_code == 201
    uid = created.json()["user_id"]
    doc = await fake_db["notifications"].find_one(
        {"recipient_user_id": uid, "notification_type": "investigator_invited"}
    )
    assert doc is not None
    assert doc["title"] == "Investigator account created"


@pytest.mark.asyncio
async def test_notification_admin_role_and_account_status(api_client, fake_db) -> None:
    admin_h = await _admin_headers(api_client, fake_db)
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="notif-target-tok"):
        signup = await api_client.post(
            "/auth/signup",
            json={"email": "notif-target@luneta.dev", "password": "Password123!", "nickname": "nftarget"},
        )
        uid = signup.json()["user_id"]
        await api_client.post("/auth/verify-email", json={"token": "notif-target-tok"})
    target_h = await _signup_and_promote(
        api_client, fake_db, email="notif-target@luneta.dev", role="registered", token="notif-target-tok"
    )

    role_patch = await api_client.patch(
        f"/admin/users/{uid}/role",
        json={"role": "investigator"},
        headers=admin_h,
    )
    assert role_patch.status_code == 200
    role_rows = await _notifs_of_type(api_client, target_h, "user_role_changed")
    assert len(role_rows) == 1
    assert role_rows[0]["payload"]["new_role"] == "investigator"

    disabled = await api_client.patch(
        f"/admin/users/{uid}/account-status",
        json={"account_status": "disabled"},
        headers=admin_h,
    )
    assert disabled.status_code == 200
    disabled_doc = await fake_db["notifications"].find_one(
        {"recipient_user_id": uid, "notification_type": "account_disabled"}
    )
    assert disabled_doc is not None

    reactivated = await api_client.patch(
        f"/admin/users/{uid}/account-status",
        json={"account_status": "active"},
        headers=admin_h,
    )
    assert reactivated.status_code == 200
    login = await api_client.post(
        "/auth/login",
        json={"email": "notif-target@luneta.dev", "password": "Password123!"},
    )
    assert login.status_code == 200
    target_h2 = {"Authorization": f"Bearer {login.json()['access_token']}"}
    reactivated_rows = await _notifs_of_type(api_client, target_h2, "account_reactivated")
    assert len(reactivated_rows) == 1


@pytest.mark.asyncio
async def test_notification_password_changed(api_client, fake_db) -> None:
    headers = await _signup_and_promote(
        api_client, fake_db, email="notif-pw@luneta.dev", role="registered", token="notif-pw-tok"
    )
    change = await api_client.post(
        "/auth/me/change-password",
        headers=headers,
        json={"current_password": "Password123!", "new_password": "Password456!"},
    )
    assert change.status_code == 204
    rows = await _notifs_of_type(api_client, headers, "password_changed")
    assert len(rows) == 1
    assert rows[0]["title"] == "Password changed"
