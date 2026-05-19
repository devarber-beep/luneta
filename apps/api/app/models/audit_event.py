"""Persistence model for platform audit trail."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AuditActionType, AuditSubjectType, UserRole


class AuditEventModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    actor_user_id: str
    actor_role: UserRole
    action_type: AuditActionType
    subject_type: AuditSubjectType
    subject_id: str
    previous: dict[str, Any] | None = None
    current: dict[str, Any] | None = None
    created_at: datetime
