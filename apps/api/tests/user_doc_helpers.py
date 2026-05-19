"""Shared user document builders for tests (in-memory Mongo)."""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.security import hash_password


def user_doc(
    *,
    email: str,
    role: str,
    password_plain: str = "UserPass123!",
    account_status: str = "active",
    verified: bool = True,
    nickname: str | None = None,
) -> dict:
    now = datetime.now(UTC)
    normalized = email.strip().lower()
    nick = nickname or normalized.split("@")[0][:10] or "user"
    return {
        "email_normalized": normalized,
        "password_hash": hash_password(password_plain),
        "password_updated_at": now,
        "role": role,
        "account_status": account_status,
        "email_verified_at": now if verified else None,
        "nickname": nick,
        "nickname_normalized": nick.lower(),
        "first_name": None,
        "last_name": None,
        "organization": None,
        "biography": None,
        "avatar": None,
        "must_change_password": False,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    }
