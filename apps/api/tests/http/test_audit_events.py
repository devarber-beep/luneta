"""Audit trail for admin user actions."""
from __future__ import annotations

import pytest

from tests.conftest import user_doc


@pytest.mark.asyncio
async def test_admin_create_investigator_writes_audit_event(api_client, fake_db) -> None:
    await fake_db["users"].insert_one(user_doc(email="admrf1@luneta.dev", role="admin", password_plain="AdminPass123!"))
    login = await api_client.post(
        "/auth/login",
        json={"email": "admrf1@luneta.dev", "password": "AdminPass123!"},
    )
    token = login.json()["access_token"]
    created = await api_client.post(
        "/admin/users/investigators",
        json={"email": "auditinv@luneta.dev", "nickname": "auditinv"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert created.status_code == 201
    inv_id = created.json()["user_id"]

    events = fake_db["audit_events"]._docs
    assert len(events) >= 1
    match = [e for e in events if e.get("subject_id") == inv_id]
    assert match
    assert match[0]["action_type"] == "investigator_account_created"
    assert match[0]["subject_type"] == "user"
