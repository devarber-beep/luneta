"""Admin audit trail read API."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import user_doc


@pytest.mark.asyncio
async def test_non_admin_cannot_list_audit_events(api_client, fake_db) -> None:
    await fake_db["users"].insert_one(
        user_doc(email="inv-audit@luneta.dev", role="investigator", password_plain="InvPass123!")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "inv-audit@luneta.dev", "password": "InvPass123!"},
    )
    token = login.json()["access_token"]
    response = await api_client.get(
        "/admin/audit-events",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_lists_and_filters_audit_events(api_client, fake_db) -> None:
    admin = user_doc(email="adm-audit@luneta.dev", role="admin", password_plain="AdminPass123!")
    insert = await fake_db["users"].insert_one(admin)
    admin_id = str(insert.inserted_id)

    now = datetime.now(UTC)
    older = now - timedelta(days=2)
    await fake_db["audit_events"].insert_one(
        {
            "actor_user_id": admin_id,
            "actor_role": "admin",
            "action_type": "investigator_account_created",
            "subject_type": "user",
            "subject_id": "user-target-1",
            "previous": None,
            "current": {"email": "new@luneta.dev"},
            "created_at": older,
        }
    )
    await fake_db["audit_events"].insert_one(
        {
            "actor_user_id": admin_id,
            "actor_role": "admin",
            "action_type": "scenario_published",
            "subject_type": "scenario",
            "subject_id": "scenario-abc",
            "previous": {"state": "in_review"},
            "current": {"state": "published"},
            "created_at": now,
        }
    )

    login = await api_client.post(
        "/auth/login",
        json={"email": "adm-audit@luneta.dev", "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    catalog = await api_client.get("/admin/audit-events/catalog", headers=headers)
    assert catalog.status_code == 200
    assert any(row["value"] == "scenario_published" for row in catalog.json()["action_types"])

    listed = await api_client.get("/admin/audit-events", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["action_type"] == "scenario_published"
    assert body["items"][0]["actor_nickname"] == admin["nickname"]

    by_subject = await api_client.get(
        "/admin/audit-events",
        params={"subject_type": "scenario", "subject_id": "scenario-abc"},
        headers=headers,
    )
    assert by_subject.status_code == 200
    assert by_subject.json()["total"] == 1

    by_action = await api_client.get(
        "/admin/audit-events",
        params={"action_type": "investigator_account_created"},
        headers=headers,
    )
    assert by_action.status_code == 200
    assert by_action.json()["total"] == 1

    detail = await api_client.get(
        f"/admin/audit-events/{body['items'][0]['id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["subject_id"] == "scenario-abc"


@pytest.mark.asyncio
async def test_patch_draft_writes_scenario_content_updated_audit(api_client, fake_db) -> None:
    headers = await _signup_investigator_headers(api_client, fake_db)
    create = await api_client.post(
        "/scenarios",
        json={"title": "Audit draft", "description": "Initial paragraph."},
        headers=headers,
    )
    assert create.status_code in (200, 201)
    sid = create.json()["id"]
    patched = await api_client.patch(
        f"/scenarios/{sid}",
        json={"description": "Updated paragraph."},
        headers=headers,
    )
    assert patched.status_code == 200
    event = await fake_db["audit_events"].find_one({"action_type": "scenario_content_updated"})
    assert event is not None
    assert event["subject_id"] == sid
    assert event["current"]["revision_number"] >= 2
    assert "description" in event["current"]["changed_fields"]


async def _signup_investigator_headers(api_client, fake_db) -> dict[str, str]:
    from unittest.mock import patch

    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="audit-patch"):
        await api_client.post(
            "/auth/signup",
            json={
                "email": "inv-audit-patch@luneta.dev",
                "password": "Password123!",
                "nickname": "invpatch",
            },
        )
        await api_client.post("/auth/verify-email", json={"token": "audit-patch"})
    await fake_db["users"].update_one(
        {"email_normalized": "inv-audit-patch@luneta.dev"},
        {"$set": {"role": "investigator"}},
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "inv-audit-patch@luneta.dev", "password": "Password123!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_investigator_writes_listable_audit_event(api_client, fake_db) -> None:
    await fake_db["users"].insert_one(
        user_doc(email="adm-audit2@luneta.dev", role="admin", password_plain="AdminPass123!")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "adm-audit2@luneta.dev", "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = await api_client.post(
        "/admin/users/investigators",
        json={"email": "listed-inv@luneta.dev", "nickname": "listedinv"},
        headers=headers,
    )
    assert created.status_code == 201
    inv_id = created.json()["user_id"]

    listed = await api_client.get(
        "/admin/audit-events",
        params={"action_type": "investigator_account_created", "subject_id": inv_id},
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
