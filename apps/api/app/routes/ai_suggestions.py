"""Ephemeral AI improvement suggestions for scenario owners."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_active_user_with_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.ai_suggestion_decisions import AiSuggestionDecisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.schemas.ai_suggestions import (
    AiSuggestionActionRequest,
    AiSuggestionActionResponse,
    AiSuggestionGenerateRequest,
    AiSuggestionGenerateResponse,
)
from app.services.ai_suggestion_service import AiSuggestionService

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> AiSuggestionService:
    return AiSuggestionService(
        scenarios_repo=ScenariosRepository(db),
        audit_repo=AuditEventsRepository(db),
        ai_decisions_repo=AiSuggestionDecisionsRepository(db),
    )


@router.post(
    "/{scenario_id}/ai-suggestions/generate",
    response_model=AiSuggestionGenerateResponse,
)
async def generate_ai_suggestions(
    scenario_id: str,
    body: AiSuggestionGenerateRequest | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.SCENARIO_UPDATE_OWN)
    ),
) -> AiSuggestionGenerateResponse:
    payload = body or AiSuggestionGenerateRequest()
    return await _service(db).generate(
        scenario_id=scenario_id,
        current_user=current_user,
        draft_title=payload.title,
        draft_description=payload.description,
    )


@router.post(
    "/{scenario_id}/ai-suggestions/{item_id}/applied",
    response_model=AiSuggestionActionResponse,
)
async def record_ai_suggestion_applied(
    scenario_id: str,
    item_id: str,
    body: AiSuggestionActionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.SCENARIO_UPDATE_OWN)
    ),
) -> AiSuggestionActionResponse:
    await _service(db).record_applied(
        scenario_id=scenario_id,
        item_id=item_id,
        current_user=current_user,
        request_id=body.request_id,
        scope=body.scope,
        kind=body.kind,
        paragraph_index=body.paragraph_index,
        current_excerpt=body.current_excerpt,
        proposed_text=body.proposed_text,
        rationale=body.rationale,
    )
    return AiSuggestionActionResponse()


@router.post(
    "/{scenario_id}/ai-suggestions/{item_id}/discard",
    response_model=AiSuggestionActionResponse,
)
async def record_ai_suggestion_discarded(
    scenario_id: str,
    item_id: str,
    body: AiSuggestionActionRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.SCENARIO_UPDATE_OWN)
    ),
) -> AiSuggestionActionResponse:
    await _service(db).record_discarded(
        scenario_id=scenario_id,
        item_id=item_id,
        current_user=current_user,
        request_id=body.request_id,
        scope=body.scope,
        kind=body.kind,
        paragraph_index=body.paragraph_index,
        current_excerpt=body.current_excerpt,
        proposed_text=body.proposed_text,
        rationale=body.rationale,
    )
    return AiSuggestionActionResponse()
