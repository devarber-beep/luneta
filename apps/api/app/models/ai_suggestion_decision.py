"""Persistence model for accepted/rejected ephemeral AI suggestions."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import UserRole

AiSuggestionDecisionAction = Literal["applied", "discarded"]
AiSuggestionScope = Literal["title", "description_full", "description_paragraph"]
AiSuggestionKind = Literal["clarity", "structure", "safety", "rewrite"]


class AiSuggestionDecisionModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    scenario_id: str
    request_id: str
    item_id: str
    action: AiSuggestionDecisionAction
    scope: AiSuggestionScope
    kind: AiSuggestionKind
    paragraph_index: int | None = None
    current_excerpt: str
    proposed_text: str
    rationale: str
    actor_user_id: str
    actor_role: UserRole
    created_at: datetime
