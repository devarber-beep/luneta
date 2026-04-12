"""Scenario API schemas for vertical slice."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.enums import CollaboratorRole, ScenarioState


class ScenarioSummaryResponse(BaseModel):
    id: str
    slug: str
    title: str
    state: ScenarioState
    updated_at: datetime


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
    collaborators: list["ScenarioCollaboratorResponse"]
    state: ScenarioState
    current_revision_number: int
    created_at: datetime
    updated_at: datetime


class SubmitReviewResponse(BaseModel):
    scenario_id: str
    state: ScenarioState


class ScenarioCollaboratorResponse(BaseModel):
    user_id: str
    role: CollaboratorRole
    added_at: datetime
    added_by: str


class AddCollaboratorRequest(BaseModel):
    user_id: str = Field(min_length=1)


class ScenarioCollaboratorsResponse(BaseModel):
    scenario_id: str
    collaborators: list[ScenarioCollaboratorResponse]


class ScenarioCommentCreateRequest(BaseModel):
    body_markdown: str = Field(min_length=1)
    revision_number: int | None = Field(default=None, ge=1)
    section_key: str | None = Field(default=None, min_length=1, max_length=120)
    field_path: str | None = Field(default=None, min_length=1, max_length=120)


class ScenarioCommentResponse(BaseModel):
    id: str
    scenario_id: str
    author_user_id: str
    body_markdown: str
    revision_number: int | None = None
    section_key: str | None = None
    field_path: str | None = None
    created_at: datetime
    updated_at: datetime


class ScenarioCommentsResponse(BaseModel):
    scenario_id: str
    items: list[ScenarioCommentResponse]
