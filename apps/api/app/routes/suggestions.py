"""Routes for change suggestions on scenarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.core.suggestion_access import can_see_suggestion_author_identity
from app.deps.authz import require_active_user_with_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.suggestions import SuggestionsRepository
from app.repositories.users import UsersRepository
from app.routes import scenarios as scenarios_routes
from app.schemas.suggestions import (
    AcceptSuggestionResponse,
    CreateSuggestionRequest,
    ReviewFeedbackStatusResponse,
    SuggestionListResponse,
    SuggestionResponse,
)
from app.services.audit_service import AuditService
from app.services.notifications_factory import build_notification_service
from app.services.suggestion_service import SuggestionService

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> SuggestionService:
    return SuggestionService(
        scenarios_repo=ScenariosRepository(db),
        suggestions_repo=SuggestionsRepository(db),
        users_repo=UsersRepository(db),
        assignments_repo=ReviewerAssignmentsRepository(db),
        review_events_repo=ReviewEventsRepository(db),
        revisions_repo=ScenarioRevisionsRepository(db),
        audit_service=AuditService(audit_repo=AuditEventsRepository(db)),
        notification_service=build_notification_service(db),
    )


def _to_response(suggestion, *, current_user: UserModel) -> SuggestionResponse:
    show_author = can_see_suggestion_author_identity(user=current_user)
    return SuggestionResponse(
        id=suggestion.id or "",
        scenario_id=suggestion.scenario_id,
        author_user_id=suggestion.author_user_id if show_author else "",
        author_role=suggestion.author_role,
        scope=suggestion.scope,
        kind=suggestion.kind,
        paragraph_index=suggestion.paragraph_index,
        body=suggestion.body,
        status=suggestion.status,
        scenario_state_at_creation=suggestion.scenario_state_at_creation,
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
        resolved_at=suggestion.resolved_at,
        resolved_by_user_id=suggestion.resolved_by_user_id,
        applied_at=suggestion.applied_at,
    )


@router.get("/{scenario_id}/suggestions/review-feedback", response_model=ReviewFeedbackStatusResponse)
async def get_review_feedback_status(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_SUGGESTION_CREATE)),
) -> ReviewFeedbackStatusResponse:
    status_payload = await _service(db).get_review_feedback_status(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return ReviewFeedbackStatusResponse(**status_payload)


@router.get("/{scenario_id}/suggestions", response_model=SuggestionListResponse)
async def list_suggestions(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_SUGGESTION_READ)),
) -> SuggestionListResponse:
    items = await _service(db).list_suggestions(scenario_id=scenario_id, current_user=current_user)
    return SuggestionListResponse(items=[_to_response(s, current_user=current_user) for s in items])


@router.post("/{scenario_id}/suggestions", response_model=SuggestionResponse, status_code=201)
async def create_suggestion(
    scenario_id: str,
    payload: CreateSuggestionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_SUGGESTION_CREATE)),
) -> SuggestionResponse:
    created = await _service(db).create_suggestion(
        scenario_id=scenario_id,
        current_user=current_user,
        scope=payload.scope,
        kind=payload.kind,
        paragraph_index=payload.paragraph_index,
        body=payload.body,
    )
    return _to_response(created, current_user=current_user)


@router.post("/{scenario_id}/suggestions/{suggestion_id}/accept", response_model=AcceptSuggestionResponse)
async def accept_suggestion(
    scenario_id: str,
    suggestion_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_UPDATE_OWN)),
) -> AcceptSuggestionResponse:
    suggestion, scenario = await _service(db).accept_suggestion(
        scenario_id=scenario_id,
        suggestion_id=suggestion_id,
        current_user=current_user,
    )
    return AcceptSuggestionResponse(
        suggestion=_to_response(suggestion, current_user=current_user),
        scenario=scenarios_routes._to_response_with_owner_flags(scenario, current_user=current_user),
    )


@router.post("/{scenario_id}/suggestions/{suggestion_id}/reject", response_model=SuggestionResponse)
async def reject_suggestion(
    scenario_id: str,
    suggestion_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_UPDATE_OWN)),
) -> SuggestionResponse:
    rejected = await _service(db).reject_suggestion(
        scenario_id=scenario_id,
        suggestion_id=suggestion_id,
        current_user=current_user,
    )
    return _to_response(rejected, current_user=current_user)


@router.post(
    "/{scenario_id}/suggestions/{suggestion_id}/apply-text",
    response_model=AcceptSuggestionResponse,
)
async def apply_suggestion_text(
    scenario_id: str,
    suggestion_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_UPDATE_OWN)),
) -> AcceptSuggestionResponse:
    suggestion, scenario = await _service(db).apply_accepted_suggestion_text(
        scenario_id=scenario_id,
        suggestion_id=suggestion_id,
        current_user=current_user,
    )
    return AcceptSuggestionResponse(
        suggestion=_to_response(suggestion, current_user=current_user),
        scenario=scenarios_routes._to_response_with_owner_flags(scenario, current_user=current_user),
    )
