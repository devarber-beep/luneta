"""Persistence model for review events collection."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ReviewEventType, ScenarioState, UserRole


class ReviewEventModel(BaseModel):
    """One row per workflow or edit event on a scenario.

    ``actor_user_id`` / ``actor_role`` identify the authenticated user who performed
    the action (audit vocabulary: the *actor*). This is not renamed to ``user_id`` to
    avoid confusion with other IDs on the same document (e.g. future subject/target fields).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    scenario_id: str
    event_type: ReviewEventType
    from_state: ScenarioState | None = None
    to_state: ScenarioState | None = None
    actor_user_id: str
    actor_role: UserRole
    created_at: datetime
