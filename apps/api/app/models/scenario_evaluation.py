"""Ethical evaluation submitted by a community member on a published scenario."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import EvaluationVisibility


def _validate_half_point_score(value: float) -> float:
    if value < 1 or value > 10:
        raise ValueError("score must be between 1 and 10")
    doubled = round(value * 2)
    if abs(value * 2 - doubled) > 1e-9:
        raise ValueError("score must use half-point steps")
    return value


class ScenarioEvaluationModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    scenario_id: str
    evaluator_user_id: str
    risk_score: float = Field(ge=1, le=10)
    benefit_score: float = Field(ge=1, le=10)
    detected_ethical_risk_ids: list[str] = Field(min_length=1)
    comment: str = ""
    visibility: EvaluationVisibility = EvaluationVisibility.VISIBLE
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    @field_validator("risk_score", "benefit_score")
    @classmethod
    def validate_half_point_scores(cls, value: float) -> float:
        return _validate_half_point_score(value)
