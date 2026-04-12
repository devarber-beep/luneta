"""Persistence model for internal scenario comments collection."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScenarioCommentModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    scenario_id: str
    author_user_id: str
    body_markdown: str
    revision_number: int | None = None
    section_key: str | None = None
    field_path: str | None = None
    created_at: datetime
    updated_at: datetime
