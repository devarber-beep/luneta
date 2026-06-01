"""In-app notifications HTTP API."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.user_doc_helpers import user_doc


@pytest.mark.asyncio
async def test_notifications_list_mark_read_and_count(api_client, fake_db) -> None:
    owner = user_doc(email="own-notif@luneta.dev", role="investigator", password_plain="InvPass123!")
    other = user_doc(email="oth-notif@luneta.dev", role="investigator", password_plain="InvPass123!")
    owner_insert = await fake_db["users"].insert_one(owner)
    other_insert = await fake_db["users"].insert_one(other)
    owner_id = str(owner_insert.inserted_id)
    other_id = str(other_insert.inserted_id)

    await fake_db["notifications"].insert_one(
        {
            "recipient_user_id": owner_id,
            "notification_type": "suggestion_received",
            "title": "New suggestion",
            "message": "Someone suggested a change.",
            "entity_type": "suggestion",
            "entity_id": "sug-1",
            "scenario_id": "sc-1",
            "actor_user_id": other_id,
            "link_path": "/scenarios/sc-1/edit",
            "payload": None,
            "read_at": None,
            "created_at": datetime.now(UTC),
        }
    )

    login = await api_client.post(
        "/auth/login",
        json={"email": "own-notif@luneta.dev", "password": "InvPass123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    listed = await api_client.get("/notifications", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["unread_count"] == 1
    notif_id = body["items"][0]["id"]

    count = await api_client.get("/notifications/unread-count", headers=headers)
    assert count.json()["unread_count"] == 1

    marked = await api_client.post(f"/notifications/{notif_id}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    assert (await api_client.get("/notifications/unread-count", headers=headers)).json()["unread_count"] == 0
