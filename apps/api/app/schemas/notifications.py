"""User notification API schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: str
    notification_type: str
    title: str
    message: str | None = None
    entity_type: str
    entity_id: str
    scenario_id: str | None = None
    actor_user_id: str | None = None
    link_path: str | None = None
    payload: dict[str, Any] | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total: int
    page: int
    page_size: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int
