"""Persistence model for review events collection."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ReviewEventType, ScenarioState


class ReviewEventModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    scenario_id: str
    event_type: ReviewEventType
    from_state: ScenarioState | None = None
    to_state: ScenarioState | None = None
    actor_user_id: str
    created_at: datetime
