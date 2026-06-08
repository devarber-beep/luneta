"""Shared helpers for writing scenario lifecycle rows to the audit trail."""
from __future__ import annotations

from typing import Any

from app.domain.enums import AuditActionType, AuditSubjectType, ScenarioState
from app.models.user import UserModel
from app.services.audit_service import AuditService


async def record_scenario_audit(
    audit: AuditService | None,
    *,
    actor: UserModel,
    action_type: AuditActionType,
    scenario_id: str,
    from_state: ScenarioState | None = None,
    to_state: ScenarioState | None = None,
    current_extra: dict[str, Any] | None = None,
) -> None:
    if audit is None:
        return
    current: dict[str, Any] = {}
    if to_state is not None:
        current["state"] = to_state.value
    if current_extra:
        current.update(current_extra)
    previous: dict[str, Any] | None = None
    if from_state is not None:
        previous = {"state": from_state.value}
    await audit.record(
        actor=actor,
        action_type=action_type,
        subject_type=AuditSubjectType.SCENARIO,
        subject_id=scenario_id,
        previous=previous,
        current=current or None,
    )


async def record_revision_snapshot_audit(
    audit: AuditService | None,
    *,
    actor: UserModel,
    scenario_id: str,
    revision_number: int,
    change_summary: str | None = None,
) -> None:
    if audit is None:
        return
    current: dict[str, Any] = {"revision_number": revision_number}
    if change_summary:
        current["change_summary"] = change_summary
    await audit.record(
        actor=actor,
        action_type=AuditActionType.SCENARIO_REVISION_SNAPSHOT,
        subject_type=AuditSubjectType.SCENARIO,
        subject_id=scenario_id,
        current=current,
    )
