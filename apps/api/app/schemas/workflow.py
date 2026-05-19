"""Workflow API schemas for review and publish actions."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ReviewOutcome, ScenarioState


class ReviewQueueItem(BaseModel):
    scenario_id: str
    title: str
    author_user_id: str
    state: ScenarioState
    has_prior_approval: bool = False
    submitted_at: datetime | None = None
    live_public_title: str | None = None
    live_public_description: str | None = None
    live_public_path: str | None = None


class ReviewedScenarioItem(BaseModel):
    scenario_id: str
    title: str
    author_user_id: str
    state: ScenarioState
    last_reviewed_at: datetime
    last_review_outcome: ReviewOutcome | None = None
    live_public_path: str | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]


class ReviewedListResponse(BaseModel):
    items: list[ReviewedScenarioItem]


class RequestChangesBody(BaseModel):
    note: str = Field(min_length=1, max_length=4000)


class MarkNotSuitableBody(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class WorkflowActionResponse(BaseModel):
    scenario_id: str
    state: ScenarioState
    changed_at: datetime
