"""Persistence model for scenario revisions collection."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ScenarioState


class ScenarioRevisionModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    scenario_id: str
    revision_number: int
    title: str
    body_markdown: str
    state_snapshot: ScenarioState
    created_by_user_id: str
    created_at: datetime
