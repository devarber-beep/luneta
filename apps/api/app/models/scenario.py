"""Persistence model for scenarios collection."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CollaboratorRole, ScenarioState


class ScenarioCollaboratorModel(BaseModel):
    user_id: str
    role: CollaboratorRole
    added_at: datetime
    added_by: str


class ScenarioModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    slug: str
    title: str
    body_markdown: str
    author_user_id: str
    collaborators: list[ScenarioCollaboratorModel] = Field(default_factory=list)
    state: ScenarioState = ScenarioState.DRAFT
    current_revision_number: int = 1
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
