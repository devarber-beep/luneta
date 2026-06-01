"""Notifications repository with fake Mongo."""
from __future__ import annotations

import pytest

from app.domain.enums import NotificationEntityType, NotificationType
from app.repositories.notifications import NotificationsRepository
from tests.conftest import FakeDB


@pytest.mark.asyncio
async def test_create_list_mark_read_and_count_unread() -> None:
    db = FakeDB()
    repo = NotificationsRepository(db)

    created = await repo.create(
        recipient_user_id="user-a",
        notification_type=NotificationType.SUGGESTION_RECEIVED,
        title="New suggestion on your scenario",
        entity_type=NotificationEntityType.SUGGESTION,
        entity_id="sug-1",
        scenario_id="sc-1",
        actor_user_id="user-b",
        link_path="/scenarios/sc-1/edit",
        payload={"suggestion_id": "sug-1"},
    )
    assert created.id
    assert created.read_at is None

    unread = await repo.count_unread(recipient_user_id="user-a")
    assert unread == 1

    items, total = await repo.list_for_recipient(recipient_user_id="user-a")
    assert total == 1
    assert items[0].notification_type == NotificationType.SUGGESTION_RECEIVED

    marked = await repo.mark_read(
        notification_id=created.id or "",
        recipient_user_id="user-a",
    )
    assert marked is not None
    assert marked.read_at is not None

    assert await repo.count_unread(recipient_user_id="user-a") == 0

    other_user_cannot = await repo.mark_read(
        notification_id=created.id or "",
        recipient_user_id="user-b",
    )
    assert other_user_cannot is None


@pytest.mark.asyncio
async def test_mark_all_read() -> None:
    db = FakeDB()
    repo = NotificationsRepository(db)
    for idx in range(3):
        await repo.create(
            recipient_user_id="user-c",
            notification_type=NotificationType.SCENARIO_REVIEW_PUBLISHED,
            title=f"Published #{idx}",
            entity_type=NotificationEntityType.SCENARIO,
            entity_id="sc-9",
            scenario_id="sc-9",
        )
    assert await repo.count_unread(recipient_user_id="user-c") == 3
    updated = await repo.mark_all_read(recipient_user_id="user-c")
    assert updated == 3
    assert await repo.count_unread(recipient_user_id="user-c") == 0
