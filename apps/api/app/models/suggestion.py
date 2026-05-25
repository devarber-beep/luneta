"""Persistence model for change suggestions on scenarios."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ScenarioState, SuggestionKind, SuggestionScope, SuggestionStatus, UserRole


class SuggestionModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    scenario_id: str
    author_user_id: str
    author_role: UserRole
    scope: SuggestionScope
    kind: SuggestionKind
    paragraph_index: int | None = None
    body: str
    status: SuggestionStatus = SuggestionStatus.PENDING
    scenario_state_at_creation: ScenarioState
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    applied_at: datetime | None = None
