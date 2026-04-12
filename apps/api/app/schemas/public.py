"""Public read-only schemas for published scenarios."""
from datetime import datetime

from pydantic import BaseModel, Field


class PublicScenarioListItem(BaseModel):
    id: str
    slug: str
    title: str
    published_at: datetime


class PublicScenarioResponse(BaseModel):
    id: str
    slug: str
    title: str
    body_markdown: str
    published_at: datetime


class PublicScenarioCommentResponse(BaseModel):
    id: str
    author_user_id: str
    body_markdown: str
    revision_number: int | None = None
    section_key: str | None = None
    field_path: str | None = None
    created_at: datetime
    updated_at: datetime


class PublicScenarioCommentsResponse(BaseModel):
    scenario_id: str
    slug: str
    items: list[PublicScenarioCommentResponse]


class PublicScenarioCommentCreateRequest(BaseModel):
    body_markdown: str = Field(min_length=1)
    revision_number: int | None = Field(default=None, ge=1)
    section_key: str | None = Field(default=None, min_length=1, max_length=120)
    field_path: str | None = Field(default=None, min_length=1, max_length=120)
