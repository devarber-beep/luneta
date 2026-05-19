"""Login session shape, mandatory password change gate, and profile/avatar API."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def _use_real_mongo() -> bool:
    return os.environ.get("LUNETA_TEST_REAL_DB", "").strip().lower() in ("1", "true", "yes")


@pytest.mark.asyncio
async def test_login_includes_must_change_password_flag(api_client, fake_db) -> None:
    email = "mcplogin@luneta.dev"
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="mcp-login-token"):
        signup = await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "nickname": "mcplogin"},
        )
        assert signup.status_code == 200
        await api_client.post("/auth/verify-email", json={"token": "mcp-login-token"})

    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200
    body = login.json()
    assert "access_token" in body
    assert body.get("must_change_password") is False

    if not _use_real_mongo():
        await fake_db["users"].update_one(
            {"email_normalized": email.strip().lower()},
            {"$set": {"must_change_password": True}},
        )

    login2 = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login2.status_code == 200
    assert login2.json().get("must_change_password") is True


@pytest.mark.asyncio
async def test_must_change_password_allows_me_and_password_change_blocks_scenarios(api_client, fake_db) -> None:
    email = "mcpgate@luneta.dev"
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="mcp-gate-token"):
        signup = await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "nickname": "mcpgate"},
        )
        assert signup.status_code == 200
        await api_client.post("/auth/verify-email", json={"token": "mcp-gate-token"})

    if not _use_real_mongo():
        await fake_db["users"].update_one(
            {"email_normalized": email.strip().lower()},
            {"$set": {"must_change_password": True, "role": "investigator"}},
        )
    else:
        await fake_db["users"].update_one(
            {"email_normalized": email.strip().lower()},
            {"$set": {"must_change_password": True, "role": "investigator"}},
        )

    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await api_client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    blocked = await api_client.post(
        "/scenarios",
        json={"title": "Gated", "description": "Gated scenario"},
        headers=headers,
    )
    assert blocked.status_code == 403

    patch_profile = await api_client.patch(
        "/auth/me",
        json={"organization": "Lab"},
        headers=headers,
    )
    assert patch_profile.status_code == 403

    pw = await api_client.post(
        "/auth/me/change-password",
        json={"current_password": "Password123!", "new_password": "Password456!"},
        headers=headers,
    )
    assert pw.status_code == 204

    ok = await api_client.post(
        "/scenarios",
        json={"title": "After pw", "description": "After password change"},
        headers=headers,
    )
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_profile_patch_organization_after_password_ok(api_client) -> None:
    email = "mcpprof@luneta.dev"
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="mcp-prof-token"):
        await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "nickname": "mcpprof"},
        )
        await api_client.post("/auth/verify-email", json={"token": "mcp-prof-token"})

    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    profile_patch = await api_client.patch(
        "/auth/me",
        json={"organization": "Institute", "biography": "Bio line"},
        headers=headers,
    )
    assert profile_patch.status_code == 200
    data = profile_patch.json()
    assert data["organization"] == "Institute"
    assert data["biography"] == "Bio line"


@pytest.mark.asyncio
async def test_avatar_upload_uses_injected_storage(api_client) -> None:
    email = "mcpavatar@luneta.dev"
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="mcp-av-token"):
        await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "nickname": "mcpavatar"},
        )
        await api_client.post("/auth/verify-email", json={"token": "mcp-av-token"})

    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    files = {"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")}
    up = await api_client.post("/auth/me/avatar", files=files, headers=headers)
    assert up.status_code == 200
    body = up.json()
    assert body["avatar"] is not None
    assert body.get("avatar_url")

    delete = await api_client.delete("/auth/me/avatar", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["avatar"] is None


@pytest.mark.asyncio
async def test_disabled_account_cannot_login(api_client, fake_db) -> None:
    email = "mcpdis@luneta.dev"
    with patch("app.services.email_verification_service.secrets.token_urlsafe", return_value="mcp-dis-token"):
        await api_client.post(
            "/auth/signup",
            json={"email": email, "password": "Password123!", "nickname": "mcpdis"},
        )
        await api_client.post("/auth/verify-email", json={"token": "mcp-dis-token"})

    await fake_db["users"].update_one(
        {"email_normalized": email.strip().lower()},
        {"$set": {"account_status": "disabled"}},
    )

    login = await api_client.post("/auth/login", json={"email": email, "password": "Password123!"})
    assert login.status_code == 403
