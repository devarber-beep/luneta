"""Admin routes for reading the platform audit trail."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_active_user_with_permission
from app.domain.authz_permissions import Permission
from app.domain.enums import AuditActionType, AuditSubjectType
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.audit import AuditCatalogOption, AuditCatalogResponse, AuditEventItem, AuditEventListResponse
from app.services.audit_service import AuditQueryService

router = APIRouter()

_ACTION_LABELS: dict[str, str] = {
    AuditActionType.INVESTIGATOR_ACCOUNT_CREATED.value: "Investigator account created",
    AuditActionType.USER_ROLE_CHANGED.value: "User role changed",
    AuditActionType.USER_ACCOUNT_STATUS_CHANGED.value: "Account status changed",
    AuditActionType.REVIEWER_ASSIGNMENT_CREATED.value: "Reviewer assignment created",
    AuditActionType.REVIEWER_ASSIGNMENT_REMOVED.value: "Reviewer assignment removed",
    AuditActionType.EVALUATION_SUBMITTED.value: "Evaluation submitted",
    AuditActionType.EVALUATION_MODERATED.value: "Evaluation moderated",
    AuditActionType.SUGGESTION_CREATED.value: "Suggestion created",
    AuditActionType.SUGGESTION_ACCEPTED.value: "Suggestion accepted",
    AuditActionType.SUGGESTION_REJECTED.value: "Suggestion rejected",
    AuditActionType.SENSITIVE_DATA_CHECK_RUN.value: "Sensitive data check",
    AuditActionType.SCENARIO_SIMILARITY_CHECK_RUN.value: "Similarity check",
    AuditActionType.AI_SUGGESTION_BATCH_GENERATED.value: "AI suggestions generated",
    AuditActionType.AI_SUGGESTION_APPLIED.value: "AI suggestion applied",
    AuditActionType.AI_SUGGESTION_APPLY_FAILED.value: "AI suggestion apply failed",
    AuditActionType.AI_SUGGESTION_DISCARDED.value: "AI suggestion discarded",
    AuditActionType.SCENARIO_CREATED.value: "Scenario created",
    AuditActionType.SCENARIO_CONTENT_UPDATED.value: "Scenario content updated",
    AuditActionType.SCENARIO_REVISION_SNAPSHOT.value: "Scenario revision snapshot",
    AuditActionType.SCENARIO_SUBMITTED_FOR_REVIEW.value: "Submitted for review",
    AuditActionType.SCENARIO_PUBLISHED.value: "Scenario published",
    AuditActionType.SCENARIO_CHANGES_REQUESTED.value: "Changes requested",
    AuditActionType.SCENARIO_MARKED_NOT_SUITABLE.value: "Marked not suitable",
    AuditActionType.SCENARIO_REOPENED.value: "Scenario reopened",
    AuditActionType.SCENARIO_DRAFT_DELETED.value: "Draft deleted",
    AuditActionType.SCENARIO_DELETED.value: "Scenario deleted",
    AuditActionType.SCENARIO_COLLABORATOR_ADDED.value: "Collaborator added",
    AuditActionType.SCENARIO_COLLABORATOR_REMOVED.value: "Collaborator removed",
}

_SUBJECT_LABELS: dict[str, str] = {
    AuditSubjectType.USER.value: "User",
    AuditSubjectType.SCENARIO.value: "Scenario",
    AuditSubjectType.SUGGESTION.value: "Suggestion",
    AuditSubjectType.EVALUATION.value: "Evaluation",
    AuditSubjectType.CLASSIFICATION_ENTRY.value: "Classification entry",
    AuditSubjectType.ETHICAL_RISK_ENTRY.value: "Ethical risk entry",
}


def _query_service(db: AsyncIOMotorDatabase) -> AuditQueryService:
    return AuditQueryService(
        audit_repo=AuditEventsRepository(db),
        users_repo=UsersRepository(db),
        scenarios_repo=ScenariosRepository(db),
    )


def _parse_action_types(raw: str | None) -> list[AuditActionType] | None:
    if not raw or not raw.strip():
        return None
    values = [part.strip() for part in raw.split(",") if part.strip()]
    parsed: list[AuditActionType] = []
    for value in values:
        try:
            parsed.append(AuditActionType(value))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action_type: {value}",
            ) from exc
    return parsed


@router.get("/audit-events/catalog", response_model=AuditCatalogResponse)
async def audit_catalog(
    _current_user: UserModel = Depends(require_active_user_with_permission(Permission.AUDIT_EVENT_READ)),
) -> AuditCatalogResponse:
    return AuditCatalogResponse(
        action_types=[
            AuditCatalogOption(value=item.value, label=_ACTION_LABELS.get(item.value, item.value))
            for item in AuditActionType
        ],
        subject_types=[
            AuditCatalogOption(value=item.value, label=_SUBJECT_LABELS.get(item.value, item.value))
            for item in AuditSubjectType
        ],
    )


@router.get("/audit-events", response_model=AuditEventListResponse)
async def list_audit_events(
    actor_query: str | None = Query(default=None, description="Actor name or email (partial match)"),
    action_type: str | None = Query(default=None, description="Comma-separated action_type values"),
    subject_type: AuditSubjectType | None = Query(default=None),
    subject_query: str | None = Query(
        default=None,
        description="Subject search: scenario title, user name/email, or partial id for other types",
    ),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    _current_user: UserModel = Depends(require_active_user_with_permission(Permission.AUDIT_EVENT_READ)),
) -> AuditEventListResponse:
    service = _query_service(db)
    items, total = await service.list_events_enriched(
        actor_query=actor_query,
        action_types=_parse_action_types(action_type),
        subject_type=subject_type,
        subject_query=subject_query,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    return AuditEventListResponse(
        items=[AuditEventItem.model_validate(row) for row in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-events/{event_id}", response_model=AuditEventItem)
async def get_audit_event(
    event_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _current_user: UserModel = Depends(require_active_user_with_permission(Permission.AUDIT_EVENT_READ)),
) -> AuditEventItem:
    row = await _query_service(db).get_event_detail(event_id=event_id)
    return AuditEventItem.model_validate(row)
