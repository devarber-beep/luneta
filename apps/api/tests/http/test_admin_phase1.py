"""Admin profile access and reviewer–investigator assignments."""
from __future__ import annotations

import pytest

from tests.conftest import user_doc


async def _admin_token(api_client, fake_db) -> str:
    await fake_db["users"].insert_one(
        user_doc(email="phase1admin@luneta.dev", role="admin", password_plain="AdminPass123!")
    )
    login = await api_client.post(
        "/auth/login",
        json={"email": "phase1admin@luneta.dev", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_reads_and_patches_disabled_user_profile(api_client, fake_db) -> None:
    token = await _admin_token(api_client, fake_db)
    headers = {"Authorization": f"Bearer {token}"}
    ins = await fake_db["users"].insert_one(
        user_doc(
            email="disabledinv@luneta.dev",
            role="investigator",
            account_status="disabled",
            verified=False,
        )
    )
    user_id = str(ins.inserted_id)

    got = await api_client.get(f"/admin/users/{user_id}/profile", headers=headers)
    assert got.status_code == 200
    assert got.json()["account_status"] == "disabled"
    assert got.json()["email_normalized"] == "disabledinv@luneta.dev"

    patched = await api_client.patch(
        f"/admin/users/{user_id}/profile",
        json={"organization": "Lab X"},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["organization"] == "Lab X"


@pytest.mark.asyncio
async def test_admin_reviewer_assignment_and_audit(api_client, fake_db) -> None:
    token = await _admin_token(api_client, fake_db)
    headers = {"Authorization": f"Bearer {token}"}
    rev_ins = await fake_db["users"].insert_one(user_doc(email="phase1rev@luneta.dev", role="reviewer"))
    inv_ins = await fake_db["users"].insert_one(user_doc(email="phase1inv@luneta.dev", role="investigator"))
    reviewer_id = str(rev_ins.inserted_id)
    investigator_id = str(inv_ins.inserted_id)

    assign = await api_client.put(
        f"/admin/reviewers/{reviewer_id}/investigators/{investigator_id}",
        headers=headers,
    )
    assert assign.status_code == 204

    listed = await api_client.get(f"/admin/reviewers/{reviewer_id}/investigators", headers=headers)
    assert listed.status_code == 200
    assert investigator_id in listed.json()["investigator_user_ids"]

    events = fake_db["audit_events"]._docs
    created = [e for e in events if e.get("action_type") == "reviewer_assignment_created"]
    assert created

    unassign = await api_client.delete(
        f"/admin/reviewers/{reviewer_id}/investigators/{investigator_id}",
        headers=headers,
    )
    assert unassign.status_code == 204
