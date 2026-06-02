"""Content-policy checks for sensitive data and scenario similarity."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import HTTPException, status

from app.domain.enums import AuditActionType, AuditSubjectType, ScenarioState
from app.models.scenario import ScenarioModel
from app.models.user import UserModel
from app.services.audit_service import AuditService
from app.services.scenario_similarity_service import ScenarioSimilarityService, SimilarityCandidate
from app.services.sensitive_data_check import (
    SensitiveDataCheckResult,
    findings_as_dicts,
    format_finding_labels,
    scan_scenario_for_sensitive_data,
    sensitive_data_blocked_message,
)

_CONTENT_CHECK_STATES = frozenset(
    {
        ScenarioState.DRAFT,
        ScenarioState.APPLYING_CHANGES,
        ScenarioState.CHANGES_REQUIRED,
        ScenarioState.PUBLISHED,
    }
)

_ACTION_LABEL: dict[str, str] = {
    "save": "saved",
    "submit_review": "submitted for review",
}


def effective_scenario(
    scenario: ScenarioModel,
    *,
    title: str | None = None,
    description: str | None = None,
    summary: str | None = None,
) -> ScenarioModel:
    updates: dict[str, str | None] = {}
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description.strip()
    if summary is not None:
        updates["summary"] = summary
    if not updates:
        return scenario
    return scenario.model_copy(update=updates)


def should_run_content_checks(scenario: ScenarioModel) -> bool:
    return scenario.state in _CONTENT_CHECK_STATES


def _sensitive_detail(
    *,
    action: Literal["save", "submit_review"],
    sensitive: SensitiveDataCheckResult,
) -> dict[str, Any]:
    finding_types = sensitive.finding_types
    return {
        "code": "sensitive_data_detected",
        "message": sensitive_data_blocked_message(finding_types=finding_types, action=action),
        "finding_types": finding_types,
        "finding_labels": format_finding_labels(finding_types),
        "findings": findings_as_dicts(sensitive.findings),
        "action": action,
    }


def _similarity_detail(
    *,
    action: Literal["save", "submit_review"],
    candidates: list[SimilarityCandidate],
) -> dict[str, Any]:
    verb = _ACTION_LABEL[action]
    titles = [c.title for c in candidates[:5]]
    return {
        "code": "similar_scenarios_detected",
        "message": (
            f"Your scenario could not be {verb}: it looks very similar to existing published "
            "scenario(s). Change the title or description to make it clearly distinct, or review "
            "the listed scenarios before continuing."
        ),
        "action": action,
        "candidates": [
            {
                "scenario_id": c.scenario_id,
                "title": c.title,
                "score": c.score,
                "public_path": c.public_path,
            }
            for c in candidates
        ],
        "similar_titles": titles,
    }


async def enforce_content_policies(
    *,
    scenario: ScenarioModel,
    current_user: UserModel,
    audit: AuditService | None,
    similarity: ScenarioSimilarityService,
    action: Literal["save", "submit_review"],
    title: str | None = None,
    description: str | None = None,
    summary: str | None = None,
) -> None:
    if not should_run_content_checks(scenario):
        return

    effective = effective_scenario(
        scenario,
        title=title,
        description=description,
        summary=summary,
    )
    scenario_id = scenario.id or ""

    sensitive_check = scan_scenario_for_sensitive_data(effective)
    if audit is not None and action == "submit_review":
        await audit.record(
            actor=current_user,
            action_type=AuditActionType.SENSITIVE_DATA_CHECK_RUN,
            subject_type=AuditSubjectType.SCENARIO,
            subject_id=scenario_id,
            current={
                "passed": sensitive_check.passed,
                "finding_types": sensitive_check.finding_types,
                "finding_count": len(sensitive_check.findings),
                "action": action,
            },
        )
    if not sensitive_check.passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_sensitive_detail(action=action, sensitive=sensitive_check),
        )

    similarity_result = await similarity.check(
        title=effective.title,
        description=effective.description,
        actor=current_user,
        exclude_scenario_id=scenario_id or None,
    )
    if similarity_result.candidates and action == "submit_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_similarity_detail(action=action, candidates=similarity_result.candidates),
        )
