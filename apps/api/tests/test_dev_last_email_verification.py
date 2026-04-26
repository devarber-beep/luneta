"""Dev-only endpoint for last issued email verification token."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.dev_email_verification_snapshot import clear_last
from app.settings import settings


@pytest.fixture(autouse=True)
def _reset_dev_email_snapshot() -> None:
    clear_last()
    yield
    clear_last()


@pytest.mark.asyncio
async def test_dev_last_email_verification_disabled_by_default(api_client) -> None:
    r = await api_client.get("/auth/dev/last-email-verification")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_dev_last_email_verification_returns_last_signup_token(api_client) -> None:
    verify_token = "dev-snapshot-token"
    with (
        patch.object(settings, "dev_expose_last_email_verification_token", True),
        patch("app.services.email_verification_service.secrets.token_urlsafe", return_value=verify_token),
    ):
        signup = await api_client.post(
            "/auth/signup",
            json={
                "email": "snap@luneta.dev",
                "password": "Password123!",
                "role": "investigator",
                "nickname": "snap",
            },
        )
        assert signup.status_code == 200

        last = await api_client.get("/auth/dev/last-email-verification")
        assert last.status_code == 200
        body = last.json()
        assert body["email"] == "snap@luneta.dev"
        assert body["token"] == verify_token
        assert "issued_at" in body
