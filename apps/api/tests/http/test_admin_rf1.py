"""Admin user management and role promotion (investigator, reviewer)."""
from __future__ import annotations

import pytest

from tests.conftest import user_doc


@pytest.mark.asyncio
async def test_admin_create_investigator_returns_201(api_client, fake_db) -> None:
    await fake_db["users"].insert_one(user_doc(email="admrf1@luneta.dev", role="admin", password_plain="AdminPass123!"))
    login = await api_client.post(
        "/auth/login",
        json={"email": "admrf1@luneta.dev", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    created = await api_client.post(
        "/admin/users/investigators",
        json={"email": "invcreate@luneta.dev", "first_name": "Invcreate", "last_name": "User"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["email_normalized"] == "invcreate@luneta.dev"
    assert body["user_id"]

    doc = await fake_db["users"].find_one({"email_normalized": "invcreate@luneta.dev"})
    assert doc is not None
    assert doc["role"] == "investigator"
    assert doc["must_change_password"] is True
    assert doc["email_verified_at"] is None


@pytest.mark.asyncio
async def test_non_admin_cannot_create_investigator(api_client, fake_db) -> None:
    await fake_db["users"].insert_one(
        user_doc(email="revonly@luneta.dev", role="reviewer", password_plain="RevPass123!", first_name="Revonly", last_name="User")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "revonly@luneta.dev", "password": "RevPass123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    blocked = await api_client.post(
        "/admin/users/investigators",
        json={"email": "invcreate2@luneta.dev", "first_name": "Invcreate2", "last_name": "User"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert blocked.status_code == 403


@pytest.mark.asyncio
async def test_admin_promote_registered_to_investigator(api_client, fake_db) -> None:
    from unittest.mock import patch

    await fake_db["users"].insert_one(user_doc(email="admrf1@luneta.dev", role="admin", password_plain="AdminPass123!"))
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="reg-prom-token"):
        signup = await api_client.post(
            "/auth/signup",
            json={
                "email": "regprom@luneta.dev",
                "password": "Password123!",
                "first_name": "Regprom",
                "last_name": "User",
            },
        )
        assert signup.status_code == 200
        uid = signup.json()["user_id"]
        await api_client.post("/auth/verify-email", json={"token": "reg-prom-token"})

    admin_login = await api_client.post(
        "/auth/login",
        json={"email": "admrf1@luneta.dev", "password": "AdminPass123!"},
    )
    token = admin_login.json()["access_token"]
    patch_role = await api_client.patch(
        f"/admin/users/{uid}/role",
        json={"role": "investigator"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_role.status_code == 200
    assert patch_role.json()["role"] == "investigator"

    doc = await fake_db["users"].find_one({"email_normalized": "regprom@luneta.dev"})
    assert doc is not None
    assert doc["role"] == "investigator"


@pytest.mark.asyncio
async def test_admin_promote_investigator_to_reviewer(api_client, fake_db) -> None:
    await fake_db["users"].insert_one(user_doc(email="admrf1@luneta.dev", role="admin", password_plain="AdminPass123!"))
    await fake_db["users"].insert_one(
        user_doc(email="invrev@luneta.dev", role="investigator", password_plain="Password123!", first_name="Invrev", last_name="User")
    )
    inv = await fake_db["users"].find_one({"email_normalized": "invrev@luneta.dev"})
    assert inv is not None
    iid = str(inv["_id"])

    admin_login = await api_client.post(
        "/auth/login",
        json={"email": "admrf1@luneta.dev", "password": "AdminPass123!"},
    )
    token = admin_login.json()["access_token"]
    patch_role = await api_client.patch(
        f"/admin/users/{iid}/role",
        json={"role": "reviewer"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_role.status_code == 200
    assert patch_role.json()["role"] == "reviewer"


@pytest.mark.asyncio
async def test_admin_deactivate_blocks_login(api_client, fake_db) -> None:
    from unittest.mock import patch

    await fake_db["users"].insert_one(user_doc(email="admrf1@luneta.dev", role="admin", password_plain="AdminPass123!"))
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="dis-user-token"):
        signup = await api_client.post(
            "/auth/signup",
            json={
                "email": "todeact@luneta.dev",
                "password": "Password123!",
                "first_name": "Todeact",
                "last_name": "User",
            },
        )
        uid = signup.json()["user_id"]
        await api_client.post("/auth/verify-email", json={"token": "dis-user-token"})

    admin_login = await api_client.post(
        "/auth/login",
        json={"email": "admrf1@luneta.dev", "password": "AdminPass123!"},
    )
    token = admin_login.json()["access_token"]
    de = await api_client.patch(
        f"/admin/users/{uid}/account-status",
        json={"account_status": "disabled"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert de.status_code == 200

    blocked = await api_client.post(
        "/auth/login",
        json={"email": "todeact@luneta.dev", "password": "Password123!"},
    )
    assert blocked.status_code == 403
