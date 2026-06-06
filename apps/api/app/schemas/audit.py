"""Admin audit trail API schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEventItem(BaseModel):
    id: str
    actor_user_id: str
    actor_display_name: str | None = None
    actor_email_normalized: str | None = None
    actor_role: str
    action_type: str
    subject_type: str
    subject_id: str
    previous: dict[str, Any] | None = None
    current: dict[str, Any] | None = None
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventItem]
    total: int
    page: int
    page_size: int


class AuditCatalogOption(BaseModel):
    value: str
    label: str


class AuditCatalogResponse(BaseModel):
    action_types: list[AuditCatalogOption]
    subject_types: list[AuditCatalogOption]
