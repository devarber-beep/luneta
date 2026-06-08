"""Scenario API schemas for vertical slice."""
from __future__ import annotations
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.domain.enums import CollaboratorRole, ScenarioState
from app.models.scenario_usage_context import ScenarioUsageContextModel


class ScenarioParticipationRole(StrEnum):
    OWNER = "owner"
    COLLABORATOR = "collaborator"


class ScenarioSummaryResponse(BaseModel):
    id: str
    title: str
    state: ScenarioState
    updated_at: datetime
    first_published_at: datetime | None = None
    public_path: str | None = None
    my_participation_role: ScenarioParticipationRole


class ScenarioCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=2000)


class ScenarioPatchRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    summary: str | None = Field(default=None, max_length=500)
    categories: list[str] | None = None
    tags: list[str] | None = None
    category_ids: list[str] | None = None
    ethical_risk_ids: list[str] | None = None
    usage_context: ScenarioUsageContextModel | None = None
    sensitive_data_involved: bool | None = None


class ScenarioAssetResponse(BaseModel):
    asset_id: str
    storage_key: str
    url: str | None = None
    alt_text: str | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str
    order: int = 0


class ScenarioAssessmentResponse(BaseModel):
    level: str
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ScenarioResponse(BaseModel):
    id: str
    title: str
    description: str
    category_ids: list[str] = Field(default_factory=list)
    ethical_risk_ids: list[str] = Field(default_factory=list)
    usage_context: ScenarioUsageContextModel | None = None
    author_user_id: str
    author_university: str | None = None
    collaborators: list["ScenarioCollaboratorResponse"]
    state: ScenarioState
    current_revision_number: int
    submitted_for_review_at: datetime | None = None
    submitted_for_review_by_user_id: str | None = None
    review_feedback_note: str | None = None
    review_feedback_at: datetime | None = None
    not_suitable_reason: str | None = None
    not_suitable_at: datetime | None = None
    approved_at: datetime | None = None
    first_approved_at: datetime | None = None
    approved_by_user_id: str | None = None
    published_at: datetime | None = None
    first_published_at: datetime | None = None
    published_by_user_id: str | None = None
    public_revision_number: int | None = None
    last_state_changed_at: datetime
    summary: str | None = None
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    keywords_normalized: list[str] = Field(default_factory=list)
    cover_image: ScenarioAssetResponse | None = None
    inline_assets: list[ScenarioAssetResponse] = Field(default_factory=list)
    ethical_considerations: ScenarioAssessmentResponse | None = None
    risk_assessment: ScenarioAssessmentResponse | None = None
    sensitive_data_involved: bool | None = None
    avg_rating: float | None = None
    rating_count: int = 0
    rating_sum: int = 0
    favorites_count: int = 0
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    live_public_title: str | None = None
    live_public_description: str | None = None
    can_create_suggestion: bool = False
    my_participation_role: ScenarioParticipationRole | None = None
    similarity_advisory: SimilarityAdvisoryResponse | None = None


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


class ReorderInlineAssetsRequest(BaseModel):
    asset_ids: list[str]


class ScenarioAssetReadUrlResponse(BaseModel):
    asset_id: str
    signed_url: str
    expires_in_seconds: int


class SimilarityCandidateResponse(BaseModel):
    scenario_id: str
    title: str
    score: float
    public_path: str | None = None


class SimilarityAdvisoryResponse(BaseModel):
    provider: str
    candidates: list[SimilarityCandidateResponse] = Field(default_factory=list)


class ScenarioRevisionListItem(BaseModel):
    revision_number: int
    title: str
    description: str
    state_snapshot: ScenarioState
    created_at: datetime
    created_by_user_id: str
    accepted_suggestion_id: str | None = None
    change_summary: str | None = None


class ScenarioRevisionsResponse(BaseModel):
    scenario_id: str
    items: list[ScenarioRevisionListItem]
