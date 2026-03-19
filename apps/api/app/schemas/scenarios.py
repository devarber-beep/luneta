"""Scenario API schemas for vertical slice."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import ScenarioState


class ScenarioCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    body_markdown: str = Field(min_length=1)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ScenarioPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    body_markdown: str | None = Field(default=None, min_length=1)


class ScenarioResponse(BaseModel):
    id: str
    slug: str
    title: str
    body_markdown: str
    author_user_id: str
    state: ScenarioState
    current_revision_number: int
    created_at: datetime
    updated_at: datetime


class SubmitReviewResponse(BaseModel):
    scenario_id: str
    state: ScenarioState
