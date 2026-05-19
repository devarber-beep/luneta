"""Reviewer ↔ investigator portfolio assignment."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewerAssignmentModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    reviewer_user_id: str
    investigator_user_id: str
    created_at: datetime

    model_config = {"populate_by_name": True}
