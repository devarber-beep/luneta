"""In-app notification persisted for each recipient."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import NotificationEntityType, NotificationType


class NotificationModel(BaseModel):
    """One row per recipient and event (reviewers get one row each on submit)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    recipient_user_id: str
    notification_type: NotificationType
    title: str
    message: str | None = None
    entity_type: NotificationEntityType
    entity_id: str
    scenario_id: str | None = None
    actor_user_id: str | None = None
    link_path: str | None = None
    payload: dict[str, Any] | None = None
    read_at: datetime | None = None
    created_at: datetime
