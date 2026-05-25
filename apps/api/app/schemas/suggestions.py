"""API schemas for change suggestions."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ScenarioState, SuggestionKind, SuggestionScope, SuggestionStatus, UserRole


class CreateSuggestionRequest(BaseModel):
    scope: SuggestionScope
    kind: SuggestionKind
    paragraph_index: int | None = None
    body: str = Field(min_length=1, max_length=20000)


class SuggestionResponse(BaseModel):
    id: str
    scenario_id: str
    author_user_id: str
    author_role: UserRole
    scope: SuggestionScope
    kind: SuggestionKind
    paragraph_index: int | None
    body: str
    status: SuggestionStatus
    scenario_state_at_creation: ScenarioState
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    applied_at: datetime | None = None


class SuggestionListResponse(BaseModel):
    items: list[SuggestionResponse]


class DescriptionParagraphsResponse(BaseModel):
    paragraphs: list[str]


class ReviewFeedbackStatusResponse(BaseModel):
    has_submitted_feedback: bool


class AcceptSuggestionResponse(BaseModel):
    suggestion: SuggestionResponse
    scenario: "ScenarioResponse"


from app.schemas.scenarios import ScenarioResponse  # noqa: E402

AcceptSuggestionResponse.model_rebuild()
