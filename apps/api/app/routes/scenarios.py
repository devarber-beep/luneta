"""Scenario routes for create/read/edit/submit-review."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.permissions import get_collaborator_role, has_republication_pending
from app.core.scenario_access import can_start_editing_working_copy
from app.domain.enums import CollaboratorRole
from app.db import get_db
from app.deps.authz import (
    require_active_user_with_permission,
    require_any_active_permission,
    require_any_permission,
    require_permission,
)
from app.domain.authz_permissions import Permission
from app.domain.enums import ScenarioState
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.suggestions import SuggestionsRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.scenarios import (
    ReorderInlineAssetsRequest,
    ScenarioCreateRequest,
    ScenarioCollaboratorsResponse,
    ScenarioCollaboratorResponse,
    ScenarioPatchRequest,
    ScenarioResponse,
    SimilarityAdvisoryResponse,
    SimilarityCandidateResponse,
    ScenarioParticipationRole,
    ScenarioRevisionListItem,
    ScenarioRevisionsResponse,
    ScenarioSummaryResponse,
    StartEditingWorkingCopyResponse,
    ScenarioAssetReadUrlResponse,
    SubmitReviewResponse,
)
from app.services.audit_service import AuditService
from app.services.notifications_factory import build_notification_service
from app.services.scenario_service import ScenarioService
from app.services.content_policy import SimilarityAdvisory
from app.services.scenario_service import ScenarioSaveResult
from app.services.scenario_similarity_service import ScenarioSimilarityService
from app.services.suggestion_service import SuggestionService
from app.storage.minio_storage import MinioScenarioStorage

router = APIRouter()


def _audit(db: AsyncIOMotorDatabase) -> AuditService:
    return AuditService(audit_repo=AuditEventsRepository(db))


def _service(db: AsyncIOMotorDatabase) -> ScenarioService:
    return ScenarioService(
        scenarios_repo=ScenariosRepository(db),
        revisions_repo=ScenarioRevisionsRepository(db),
        review_events_repo=ReviewEventsRepository(db),
        users_repo=UsersRepository(db),
        assignments_repo=ReviewerAssignmentsRepository(db),
        classification_repo=ScenarioClassificationRepository(db),
        ethical_repo=EthicalRisksRepository(db),
        audit_service=_audit(db),
        similarity_service=_similarity_service(db),
        notification_service=build_notification_service(db),
    )


def _similarity_service(db: AsyncIOMotorDatabase) -> ScenarioSimilarityService:
    return ScenarioSimilarityService(
        scenarios_repo=ScenariosRepository(db),
        audit_service=_audit(db),
    )


def _suggestion_service(db: AsyncIOMotorDatabase) -> SuggestionService:
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


def _my_participation_role(*, scenario, user_id: str) -> ScenarioParticipationRole:
    if get_collaborator_role(scenario=scenario, user_id=user_id) == CollaboratorRole.COLLABORATOR:
        return ScenarioParticipationRole.COLLABORATOR
    return ScenarioParticipationRole.OWNER


def _similarity_advisory_response(advisory: SimilarityAdvisory | None) -> SimilarityAdvisoryResponse | None:
    if advisory is None:
        return None
    return SimilarityAdvisoryResponse(
        provider=advisory.provider,
        candidates=[
            SimilarityCandidateResponse(
                scenario_id=c.scenario_id,
                title=c.title,
                score=c.score,
                public_path=c.public_path,
            )
            for c in advisory.candidates
        ],
    )


def _to_response(
    scenario,
    *,
    similarity_advisory: SimilarityAdvisory | None = None,
) -> ScenarioResponse:
    show_live = scenario.state == ScenarioState.IN_REVIEW or has_republication_pending(scenario=scenario)
    live_title = live_description = None
    if show_live and scenario.public_slug is not None:
        live_title = scenario.public_title
        live_description = scenario.public_description
    cover_image = scenario.cover_image.model_dump() if scenario.cover_image is not None else None
    inline_assets = [asset.model_dump() for asset in scenario.inline_assets]
    return ScenarioResponse(
        id=scenario.id or "",
        title=scenario.title,
        description=scenario.description,
        category_ids=scenario.category_ids,
        ethical_risk_ids=scenario.ethical_risk_ids,
        usage_context=scenario.usage_context,
        author_user_id=scenario.author_user_id,
        author_university=scenario.author_university,
        collaborators=[
            ScenarioCollaboratorResponse(
                user_id=collaborator.user_id,
                role=collaborator.role,
                added_at=collaborator.added_at,
                added_by=collaborator.added_by,
            )
            for collaborator in scenario.collaborators
        ],
        state=scenario.state,
        current_revision_number=scenario.current_revision_number,
        submitted_for_review_at=scenario.submitted_for_review_at,
        submitted_for_review_by_user_id=scenario.submitted_for_review_by_user_id,
        review_feedback_note=scenario.review_feedback_note,
        review_feedback_at=scenario.review_feedback_at,
        not_suitable_reason=scenario.not_suitable_reason,
        not_suitable_at=scenario.not_suitable_at,
        approved_at=scenario.approved_at,
        first_approved_at=scenario.first_approved_at,
        approved_by_user_id=scenario.approved_by_user_id,
        published_at=scenario.published_at,
        first_published_at=scenario.first_published_at,
        published_by_user_id=scenario.published_by_user_id,
        public_revision_number=scenario.public_revision_number,
        last_state_changed_at=scenario.last_state_changed_at,
        summary=scenario.summary,
        categories=scenario.categories,
        tags=scenario.tags,
        keywords_normalized=scenario.keywords_normalized,
        cover_image=cover_image,
        inline_assets=inline_assets,
        ethical_considerations=scenario.ethical_considerations,
        risk_assessment=scenario.risk_assessment,
        sensitive_data_involved=scenario.sensitive_data_involved,
        avg_rating=scenario.avg_rating,
        rating_count=scenario.rating_count,
        rating_sum=scenario.rating_sum,
        favorites_count=scenario.favorites_count,
        archived_at=scenario.archived_at,
        deleted_at=scenario.deleted_at,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
        live_public_title=live_title,
        live_public_description=live_description,
        similarity_advisory=_similarity_advisory_response(similarity_advisory),
    )


def _to_response_from_save(result: ScenarioSaveResult) -> ScenarioResponse:
    return _to_response(result.scenario, similarity_advisory=result.similarity_advisory)


@router.post("", response_model=ScenarioResponse)
async def create_scenario(
    payload: ScenarioCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_CREATE_DRAFT)),
) -> ScenarioResponse:
    result = await _service(db).create_draft(
        current_user=current_user,
        title=payload.title,
        description=payload.description,
    )
    return _to_response_from_save(result)


@router.get("/mine", response_model=list[ScenarioSummaryResponse])
async def list_my_scenarios(
    q: str | None = Query(default=None, max_length=200),
    state: ScenarioState | None = Query(default=None),
    pending_suggestions: bool = Query(default=False),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SCENARIO_READ_OWN)),
) -> list[ScenarioSummaryResponse]:
    scenario_ids_filter: list[str] | None = None
    if pending_suggestions:
        participating_ids = await ScenariosRepository(db).list_participating_user_ids(
            user_id=current_user.id or ""
        )
        scenario_ids_filter = await SuggestionsRepository(db).list_scenario_ids_with_pending_post_publication(
            scenario_ids=participating_ids
        )
        if not scenario_ids_filter:
            return []
    scenarios = await _service(db).list_my_scenarios(
        current_user=current_user,
        q=q,
        state=state if not pending_suggestions else None,
        scenario_ids=scenario_ids_filter,
    )
    uid = current_user.id or ""
    scenario_ids = [s.id or "" for s in scenarios if s.id]
    pending_counts = await _suggestion_service(db).pending_post_publication_counts(
        scenario_ids=scenario_ids
    )
    return [
        ScenarioSummaryResponse(
            id=s.id or "",
            title=s.title,
            state=s.state,
            updated_at=s.updated_at,
            first_published_at=s.first_published_at,
            public_path=f"/public/{s.public_slug}" if s.public_slug else None,
            my_participation_role=_my_participation_role(scenario=s, user_id=uid),
            pending_suggestion_count=pending_counts.get(s.id or "", 0),
        )
        for s in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_permission(
            Permission.SCENARIO_READ_OWN,
            Permission.SCENARIO_READ_REVIEW_QUEUE,
            Permission.SCENARIO_READ_PUBLIC,
        )
    ),
) -> ScenarioResponse:
    scenario = await _service(db).get_scenario_if_readable(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    sug_svc = _suggestion_service(db)
    can_suggest = await sug_svc.user_can_create_suggestion(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    pending_count = await sug_svc.pending_post_publication_count(scenario_id=scenario_id)
    return _to_response(scenario).model_copy(
        update={
            "can_create_suggestion": can_suggest,
            "my_participation_role": _my_participation_role(
                scenario=scenario,
                user_id=current_user.id or "",
            ),
            "pending_suggestion_count": pending_count,
            "can_start_editing_working_copy": can_start_editing_working_copy(
                user=current_user,
                scenario=scenario,
            ),
        }
    )


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def patch_scenario(
    scenario_id: str,
    payload: ScenarioPatchRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
    ),
) -> ScenarioResponse:
    raw = payload.model_dump(exclude_unset=True)
    usage_context_raw = raw.get("usage_context")
    result = await _service(db).patch_draft(
        scenario_id=scenario_id,
        current_user=current_user,
        title=raw.get("title"),
        description=raw.get("description"),
        summary=raw.get("summary"),
        categories=raw.get("categories"),
        tags=raw.get("tags"),
        category_ids=raw.get("category_ids"),
        ethical_risk_ids=raw.get("ethical_risk_ids"),
        usage_context=payload.usage_context if usage_context_raw is not None else None,
        sensitive_data_involved=raw.get("sensitive_data_involved"),
    )
    return _to_response_from_save(result)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_DELETE_OWN)),
) -> None:
    await _service(db).delete_draft(scenario_id=scenario_id, current_user=current_user)


@router.post("/{scenario_id}/submit-review", response_model=SubmitReviewResponse)
async def submit_review(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_SUBMIT_REVIEW)),
) -> SubmitReviewResponse:
    scenario = await _service(db).submit_review(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return SubmitReviewResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
    )


@router.post("/{scenario_id}/start-applying-changes", response_model=SubmitReviewResponse)
async def start_applying_changes(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_SUBMIT_REVIEW)),
) -> SubmitReviewResponse:
    scenario = await _service(db).start_applying_changes(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return SubmitReviewResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
    )


@router.post("/{scenario_id}/start-editing", response_model=StartEditingWorkingCopyResponse)
async def start_editing_working_copy(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.SCENARIO_UPDATE_OWN)),
) -> StartEditingWorkingCopyResponse:
    scenario = await _service(db).start_editing_working_copy(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return StartEditingWorkingCopyResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
    )


@router.post("/{scenario_id}/assets/cover", response_model=ScenarioResponse)
async def upload_cover_asset(
    scenario_id: str,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
    ),
) -> ScenarioResponse:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are allowed")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    scenario = await _service(db).upload_cover_image(
        scenario_id=scenario_id,
        current_user=current_user,
        storage=MinioScenarioStorage.from_settings(),
        content=content,
        content_type=content_type,
        alt_text=alt_text,
    )
    return _to_response(scenario)


@router.post("/{scenario_id}/assets/inline", response_model=ScenarioResponse)
async def upload_inline_asset(
    scenario_id: str,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    order: int = Form(default=0),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
    ),
) -> ScenarioResponse:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are allowed")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    scenario = await _service(db).upload_inline_image(
        scenario_id=scenario_id,
        current_user=current_user,
        storage=MinioScenarioStorage.from_settings(),
        content=content,
        content_type=content_type,
        alt_text=alt_text,
        order=order,
    )
    return _to_response(scenario)


@router.delete("/{scenario_id}/assets/cover", response_model=ScenarioResponse)
async def delete_cover_asset(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
    ),
) -> ScenarioResponse:
    scenario = await _service(db).remove_cover_image(
        scenario_id=scenario_id,
        current_user=current_user,
        storage=MinioScenarioStorage.from_settings(),
    )
    return _to_response(scenario)


@router.delete("/{scenario_id}/assets/inline/{asset_id}", response_model=ScenarioResponse)
async def delete_inline_asset(
    scenario_id: str,
    asset_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
    ),
) -> ScenarioResponse:
    scenario = await _service(db).remove_inline_image(
        scenario_id=scenario_id,
        asset_id=asset_id,
        current_user=current_user,
        storage=MinioScenarioStorage.from_settings(),
    )
    return _to_response(scenario)


@router.post("/{scenario_id}/assets/inline/reorder", response_model=ScenarioResponse)
async def reorder_inline_assets(
    scenario_id: str,
    payload: ReorderInlineAssetsRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
    ),
) -> ScenarioResponse:
    scenario = await _service(db).reorder_inline_images(
        scenario_id=scenario_id,
        asset_ids=payload.asset_ids,
        current_user=current_user,
    )
    return _to_response(scenario)


@router.get("/{scenario_id}/assets/{asset_id}/read-url", response_model=ScenarioAssetReadUrlResponse)
async def get_asset_read_url(
    scenario_id: str,
    asset_id: str,
    expires_in_seconds: int = 900,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_READ_OWN, Permission.SCENARIO_READ_REVIEW_QUEUE)
    ),
) -> ScenarioAssetReadUrlResponse:
    signed_url, expires = await _service(db).resolve_asset_read_url(
        scenario_id=scenario_id,
        asset_id=asset_id,
        current_user=current_user,
        storage=MinioScenarioStorage.from_settings(),
        expires_in_seconds=expires_in_seconds,
    )
    return ScenarioAssetReadUrlResponse(asset_id=asset_id, signed_url=signed_url, expires_in_seconds=expires)


@router.get("/{scenario_id}/collaborators", response_model=ScenarioCollaboratorsResponse)
async def list_collaborators(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_active_permission(Permission.SCENARIO_READ_OWN, Permission.SCENARIO_READ_REVIEW_QUEUE)
    ),
) -> ScenarioCollaboratorsResponse:
    collaborators, scenario = await _service(db).list_collaborators(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return ScenarioCollaboratorsResponse(
        scenario_id=scenario.id or "",
        collaborators=[
            ScenarioCollaboratorResponse(
                user_id=collaborator.user_id,
                role=collaborator.role,
                added_at=collaborator.added_at,
                added_by=collaborator.added_by,
            )
            for collaborator in collaborators
        ],
    )


@router.get("/{scenario_id}/revisions", response_model=ScenarioRevisionsResponse)
async def list_scenario_revisions(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_permission(
            Permission.SCENARIO_READ_OWN,
            Permission.SCENARIO_READ_REVIEW_QUEUE,
        )
    ),
) -> ScenarioRevisionsResponse:
    revisions = await _service(db).list_revisions(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return ScenarioRevisionsResponse(
        scenario_id=scenario_id,
        items=[
            ScenarioRevisionListItem(
                revision_number=row.revision_number,
                title=row.title,
                description=row.description,
                state_snapshot=row.state_snapshot,
                created_at=row.created_at,
                created_by_user_id=row.created_by_user_id,
                accepted_suggestion_id=row.accepted_suggestion_id,
                change_summary=row.change_summary,
            )
            for row in revisions
        ],
    )


