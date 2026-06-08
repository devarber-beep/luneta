"""Workflow routes for reviewer queue and transitions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_active_user_with_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.suggestions import SuggestionsRepository
from app.repositories.users import UsersRepository
from app.schemas.workflow import (
    MarkNotSuitableBody,
    RequestChangesBody,
    ReviewedListResponse,
    ReviewQueueResponse,
    WorkflowActionResponse,
)
from app.services.audit_service import AuditService
from app.services.notifications_factory import build_notification_service
from app.services.workflow_service import WorkflowService

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> WorkflowService:
    assignments = ReviewerAssignmentsRepository(db)
    return WorkflowService(
        scenarios_repo=ScenariosRepository(db),
        review_events_repo=ReviewEventsRepository(db),
        users_repo=UsersRepository(db),
        assignments_repo=assignments,
        suggestions_repo=SuggestionsRepository(db),
        notification_service=build_notification_service(db),
        audit_service=AuditService(audit_repo=AuditEventsRepository(db)),
    )


@router.get("/review-queue", response_model=ReviewQueueResponse)
async def review_queue(
    q: str | None = Query(default=None, max_length=200),
    category_id: list[str] = Query(default=[]),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_READ_REVIEW_QUEUE)),
) -> ReviewQueueResponse:
    items = await _service(db).review_queue(
        current_user=current_user,
        q=q,
        category_ids=category_id or None,
    )
    return ReviewQueueResponse(items=items)


@router.get("/reviewed", response_model=ReviewedListResponse)
async def reviewed_list(
    q: str | None = Query(default=None, max_length=200),
    category_id: list[str] = Query(default=[]),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_READ_REVIEW_QUEUE)),
) -> ReviewedListResponse:
    items = await _service(db).reviewed_list(
        current_user=current_user,
        q=q,
        category_ids=category_id or None,
    )
    return ReviewedListResponse(items=items)


@router.post("/scenarios/{scenario_id}/start-review", response_model=WorkflowActionResponse)
async def start_review(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_START_REVIEW)),
) -> WorkflowActionResponse:
    scenario, changed_at = await _service(db).start_review(scenario_id=scenario_id, current_user=current_user)
    return WorkflowActionResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
        changed_at=changed_at,
    )


@router.post("/scenarios/{scenario_id}/request-changes", response_model=WorkflowActionResponse)
async def request_changes(
    scenario_id: str,
    body: RequestChangesBody,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_REQUEST_CHANGES)),
) -> WorkflowActionResponse:
    scenario, changed_at = await _service(db).request_changes(
        scenario_id=scenario_id,
        current_user=current_user,
        note=body.note,
    )
    return WorkflowActionResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
        changed_at=changed_at,
    )


@router.post("/scenarios/{scenario_id}/mark-not-suitable", response_model=WorkflowActionResponse)
async def mark_not_suitable(
    scenario_id: str,
    body: MarkNotSuitableBody,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_MARK_NOT_SUITABLE)),
) -> WorkflowActionResponse:
    scenario, changed_at = await _service(db).mark_not_suitable(
        scenario_id=scenario_id,
        current_user=current_user,
        reason=body.reason,
    )
    return WorkflowActionResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
        changed_at=changed_at,
    )


@router.post("/scenarios/{scenario_id}/reopen", response_model=WorkflowActionResponse)
async def reopen_not_suitable(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_REOPEN_NOT_SUITABLE)),
) -> WorkflowActionResponse:
    scenario, changed_at = await _service(db).reopen(scenario_id=scenario_id, current_user=current_user)
    return WorkflowActionResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
        changed_at=changed_at,
    )


@router.post("/scenarios/{scenario_id}/publish", response_model=WorkflowActionResponse)
async def publish(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_PUBLISH)),
) -> WorkflowActionResponse:
    scenario, changed_at = await _service(db).publish(scenario_id=scenario_id, current_user=current_user)
    return WorkflowActionResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
        changed_at=changed_at,
    )
