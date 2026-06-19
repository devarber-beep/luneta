"""Scenario delete API (owner draft + admin)."""
from __future__ import annotations

from bson import ObjectId
import pytest

from tests.conftest import user_doc


@pytest.mark.asyncio
async def test_owner_can_delete_draft_and_assets(api_client, fake_db, monkeypatch) -> None:
    deleted_keys: list[str] = []

    class _Storage:
        def ensure_bucket(self) -> None:
            return None

        def delete_object(self, *, storage_key: str) -> None:
            deleted_keys.append(storage_key)

    monkeypatch.setattr(
        "app.routes.scenarios.MinioScenarioStorage.from_settings",
        lambda: _Storage(),
    )

    await fake_db["users"].insert_one(
        user_doc(email="del-owner@luneta.dev", role="investigator", password_plain="InvPass123!")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "del-owner@luneta.dev", "password": "InvPass123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = await api_client.post(
        "/scenarios",
        json={"title": "Draft to delete", "description": "Paragraph."},
        headers=headers,
    )
    sid = created.json()["id"]
    cover_key = f"scenarios/{sid}/cover/cover-1"
    inline_key = f"scenarios/{sid}/inline/inline-1"
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": cover_key,
                    "mime_type": "image/png",
                    "order": 0,
                },
                "inline_assets": [
                    {
                        "asset_id": "inline-1",
                        "storage_key": inline_key,
                        "mime_type": "image/png",
                        "order": 0,
                    }
                ],
            }
        },
    )

    deleted = await api_client.delete(f"/scenarios/{sid}", headers=headers)
    assert deleted.status_code == 204
    assert cover_key in deleted_keys
    assert inline_key in deleted_keys

    doc = await fake_db["scenarios"].find_one({"_id": ObjectId(sid)})
    assert doc["deleted_at"] is not None
    assert doc["cover_image"] is None
    assert doc["inline_assets"] == []


@pytest.mark.asyncio
async def test_admin_can_delete_scenario_and_assets(api_client, fake_db, monkeypatch) -> None:
    deleted_keys: list[str] = []

    class _Storage:
        def ensure_bucket(self) -> None:
            return None

        def delete_object(self, *, storage_key: str) -> None:
            deleted_keys.append(storage_key)

    monkeypatch.setattr(
        "app.routes.scenarios.MinioScenarioStorage.from_settings",
        lambda: _Storage(),
    )

    inv = user_doc(email="del-inv@luneta.dev", role="investigator", password_plain="InvPass123!")
    inv_insert = await fake_db["users"].insert_one(inv)
    inv_id = str(inv_insert.inserted_id)
    await fake_db["users"].insert_one(
        user_doc(email="del-other@luneta.dev", role="investigator", password_plain="InvPass123!")
    )
    await fake_db["users"].insert_one(
        user_doc(email="del-admin@luneta.dev", role="admin", password_plain="AdminPass123!")
    )

    login_inv = await api_client.post(
        "/auth/login",
        json={"email": "del-inv@luneta.dev", "password": "InvPass123!"},
    )
    inv_headers = {"Authorization": f"Bearer {login_inv.json()['access_token']}"}
    created = await api_client.post(
        "/scenarios",
        json={"title": "Scenario to delete", "description": "Paragraph."},
        headers=inv_headers,
    )
    sid = created.json()["id"]
    cover_key = f"scenarios/{sid}/cover/cover-1"
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "state": "published",
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": cover_key,
                    "mime_type": "image/png",
                    "order": 0,
                }
            }
        },
    )

    login_admin = await api_client.post(
        "/auth/login",
        json={"email": "del-admin@luneta.dev", "password": "AdminPass123!"},
    )
    admin_headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

    login_other = await api_client.post(
        "/auth/login",
        json={"email": "del-other@luneta.dev", "password": "InvPass123!"},
    )
    other_headers = {"Authorization": f"Bearer {login_other.json()['access_token']}"}

    denied = await api_client.delete(f"/scenarios/{sid}", headers=other_headers)
    assert denied.status_code == 403

    deleted = await api_client.delete(f"/scenarios/{sid}", headers=admin_headers)
    assert deleted.status_code == 204
    assert cover_key in deleted_keys

    audit = await fake_db["audit_events"].find_one({"action_type": "scenario_deleted", "subject_id": sid})
    assert audit is not None
    assert audit["actor_user_id"] != inv_id


@pytest.mark.asyncio
async def test_owner_can_delete_published_scenario(api_client, fake_db, monkeypatch) -> None:
    deleted_keys: list[str] = []

    class _Storage:
        def ensure_bucket(self) -> None:
            return None

        def delete_object(self, *, storage_key: str) -> None:
            deleted_keys.append(storage_key)

    monkeypatch.setattr(
        "app.routes.scenarios.MinioScenarioStorage.from_settings",
        lambda: _Storage(),
    )

    await fake_db["users"].insert_one(
        user_doc(email="del-pub-owner@luneta.dev", role="investigator", password_plain="InvPass123!")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "del-pub-owner@luneta.dev", "password": "InvPass123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = await api_client.post(
        "/scenarios",
        json={"title": "Published to delete", "description": "Paragraph."},
        headers=headers,
    )
    sid = created.json()["id"]
    cover_key = f"scenarios/{sid}/cover/cover-1"
    await fake_db["scenarios"].update_one(
        {"_id": ObjectId(sid)},
        {
            "$set": {
                "state": "published",
                "cover_image": {
                    "asset_id": "cover-1",
                    "storage_key": cover_key,
                    "mime_type": "image/png",
                    "order": 0,
                },
            }
        },
    )

    deleted = await api_client.delete(f"/scenarios/{sid}", headers=headers)
    assert deleted.status_code == 204
    assert cover_key in deleted_keys

    audit = await fake_db["audit_events"].find_one({"action_type": "scenario_deleted", "subject_id": sid})
    assert audit is not None
