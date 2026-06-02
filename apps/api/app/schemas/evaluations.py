"""API schemas for scenario ethical evaluations."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import EvaluationVisibility
from app.models.scenario_evaluation import _validate_half_point_score


class SubmitEvaluationRequest(BaseModel):
    risk_score: float = Field(ge=1, le=10)
    benefit_score: float = Field(ge=1, le=10)

    @field_validator("risk_score", "benefit_score")
    @classmethod
    def validate_half_point_scores(cls, value: float) -> float:
        return _validate_half_point_score(value)
    detected_ethical_risk_ids: list[str] = Field(min_length=1)
    comment: str = ""


class EvaluationResponse(BaseModel):
    id: str
    scenario_id: str
    evaluator_user_id: str
    evaluator_nickname: str | None = None
    risk_score: float
    benefit_score: float
    detected_ethical_risk_ids: list[str]
    detected_ethical_risk_labels: list[str] = Field(default_factory=list)
    comment: str
    visibility: EvaluationVisibility
    submitted_at: datetime


class MyEvaluationResponse(BaseModel):
    evaluation: EvaluationResponse | None
    can_submit: bool


class EvaluationSummaryResponse(BaseModel):
    scenario_id: str
    evaluation_count: int
    average_risk_score: float | None
    average_benefit_score: float | None
    detected_ethical_risk_labels: list[str] = Field(default_factory=list)
    comments: list[str] = Field(
        default_factory=list,
        description="Non-empty free-text comments; populated for scenario owner only.",
    )


class EvaluationListResponse(BaseModel):
    items: list[EvaluationResponse]


class ModerateEvaluationRequest(BaseModel):
    action: str = Field(description="hide or delete")


class AdminEvaluationModerationTarget(BaseModel):
    scenario_id: str
    title: str
    published_at: datetime
    evaluation_count: int


class AdminEvaluationModerationTargetsResponse(BaseModel):
    items: list[AdminEvaluationModerationTarget]
