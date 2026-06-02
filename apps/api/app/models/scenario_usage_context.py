"""Author-defined usage context for a scenario (filled by owner, not evaluators)."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.domain.ethical_field_types import DurationFrequencyOption, YesNoAnswer


class ScenarioUsageContextModel(BaseModel):
    children_age_start: int | None = Field(default=None, ge=0, le=17)
    children_age_end: int | None = Field(default=None, ge=0, le=17)
    children_count: int | None = Field(default=None, ge=1, le=500)
    duration_frequency: DurationFrequencyOption | None = None
    physically_present: YesNoAnswer | None = None
    online_present: YesNoAnswer | None = None
    execution_place_affects_scenario: YesNoAnswer | None = None
    special_circumstances: YesNoAnswer | None = None
    consent_in_place: YesNoAnswer | None = None

    @model_validator(mode="after")
    def _validate_ranges(self) -> "ScenarioUsageContextModel":
        if self.children_age_start is not None and self.children_age_end is not None:
            if self.children_age_end < self.children_age_start:
                raise ValueError("children_age_end must be >= children_age_start")
        return self

    def missing_fields(self) -> list[str]:
        missing: list[str] = []
        if self.children_age_start is None:
            missing.append("children_age_start")
        if self.children_age_end is None:
            missing.append("children_age_end")
        if self.duration_frequency is None:
            missing.append("duration_frequency")
        if self.physically_present is None:
            missing.append("physically_present")
        if self.online_present is None:
            missing.append("online_present")
        if self.execution_place_affects_scenario is None:
            missing.append("execution_place_affects_scenario")
        if self.special_circumstances is None:
            missing.append("special_circumstances")
        if self.consent_in_place is None:
            missing.append("consent_in_place")
        return missing

    def is_complete(self) -> bool:
        return not self.missing_fields()
