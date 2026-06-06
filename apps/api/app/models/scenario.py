"""Persistence model for scenarios collection."""
from __future__ import annotations

from datetime import datetime
import re
import unicodedata

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import CollaboratorRole, ScenarioState
from app.models.scenario_usage_context import ScenarioUsageContextModel


class ScenarioCollaboratorModel(BaseModel):
    user_id: str
    role: CollaboratorRole
    added_at: datetime
    added_by: str


class ScenarioAssetModel(BaseModel):
    asset_id: str
    storage_key: str
    url: str | None = None
    alt_text: str | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str
    order: int = 0


class ScenarioAssessmentModel(BaseModel):
    level: str
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


def slugify_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return base or "escenario"


class ScenarioModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    slug: str
    title: str
    description: str = ""
    category_ids: list[str] = Field(default_factory=list)
    ethical_risk_ids: list[str] = Field(default_factory=list)
    usage_context: ScenarioUsageContextModel | None = None
    author_user_id: str
    author_university: str | None = None
    author_university_normalized: str | None = None
    collaborators: list[ScenarioCollaboratorModel] = Field(default_factory=list)
    state: ScenarioState = ScenarioState.DRAFT
    current_revision_number: int = 1
    summary: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    submitted_for_review_at: datetime | None = None
    submitted_for_review_by_user_id: str | None = None
    review_started_at: datetime | None = None
    review_feedback_note: str | None = None
    review_feedback_at: datetime | None = None
    review_feedback_by_user_id: str | None = None
    not_suitable_reason: str | None = None
    not_suitable_at: datetime | None = None
    not_suitable_by_user_id: str | None = None
    last_reviewed_at: datetime | None = None
    last_reviewed_by_user_id: str | None = None
    last_review_outcome: str | None = None
    approved_at: datetime | None = None
    first_approved_at: datetime | None = None
    approved_by_user_id: str | None = None
    published_at: datetime | None = None
    first_published_at: datetime | None = None
    published_by_user_id: str | None = None
    public_revision_number: int | None = None
    last_state_changed_at: datetime
    public_title: str | None = None
    public_description: str | None = None
    public_slug: str | None = None
    keywords_normalized: list[str] = Field(default_factory=list)
    cover_image: ScenarioAssetModel | None = None
    inline_assets: list[ScenarioAssetModel] = Field(default_factory=list)
    ethical_considerations: ScenarioAssessmentModel | None = None
    risk_assessment: ScenarioAssessmentModel | None = None
    sensitive_data_involved: bool | None = None
    avg_rating: float | None = None
    rating_count: int = 0
    rating_sum: int = 0
    favorites_count: int = 0
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def published_requires_public_snapshot(self) -> Self:
        if self.published_at is None:
            return self
        if (
            not self.public_slug
            or self.public_title is None
            or self.public_description is None
        ):
            msg = "Published scenario must have public_slug, public_title and public_description"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def rating_counters_must_be_consistent(self) -> Self:
        if self.rating_count < 0 or self.rating_sum < 0 or self.favorites_count < 0:
            msg = "rating_count, rating_sum and favorites_count cannot be negative"
            raise ValueError(msg)
        if self.rating_count == 0:
            if self.avg_rating not in (None, 0):
                msg = "avg_rating must be null/0 when rating_count is 0"
                raise ValueError(msg)
            return self
        expected = self.rating_sum / self.rating_count
        if self.avg_rating is None or abs(self.avg_rating - expected) > 1e-9:
            msg = "avg_rating must equal rating_sum / rating_count"
            raise ValueError(msg)
        return self
