"""Workflow API schemas for review and publish actions."""
from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import ScenarioState


class ReviewQueueItem(BaseModel):
    scenario_id: str
    slug: str
    title: str
    author_user_id: str
    state: ScenarioState
    submitted_at: datetime | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]


class WorkflowActionResponse(BaseModel):
    scenario_id: str
    state: ScenarioState
    changed_at: datetime
