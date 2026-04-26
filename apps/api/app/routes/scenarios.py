"""Scenario routes for create/read/edit/submit-review."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.permissions import has_republication_pending
from app.db import get_db
from app.deps.authz import require_any_permission, require_permission
from app.domain.authz_permissions import Permission
from app.domain.enums import ScenarioState
from app.models.user import UserModel
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.scenarios import (
    AddCollaboratorRequest,
    ReorderInlineAssetsRequest,
    ScenarioCreateRequest,
    ScenarioCollaboratorsResponse,
    ScenarioCollaboratorResponse,
    ScenarioPatchRequest,
    ScenarioResponse,
    ScenarioSummaryResponse,
    ScenarioAssetReadUrlResponse,
    SubmitReviewResponse,
)
from app.services.mailer_service import MailerService
from app.services.scenario_service import ScenarioService
from app.storage.minio_storage import MinioScenarioStorage

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> ScenarioService:
    return ScenarioService(
        scenarios_repo=ScenariosRepository(db),
        revisions_repo=ScenarioRevisionsRepository(db),
        review_events_repo=ReviewEventsRepository(db),
        users_repo=UsersRepository(db),
        mailer=MailerService(),
    )


def _to_response(scenario) -> ScenarioResponse:
    show_live = scenario.state == ScenarioState.IN_REVIEW or has_republication_pending(scenario=scenario)
    live_slug = live_title = live_body = None
    if show_live and scenario.public_slug is not None:
        live_slug = scenario.public_slug
        live_title = scenario.public_title
        live_body = scenario.public_body_markdown
    cover_image = scenario.cover_image.model_dump() if scenario.cover_image is not None else None
    inline_assets = [asset.model_dump() for asset in scenario.inline_assets]
    return ScenarioResponse(
        id=scenario.id or "",
        slug=scenario.slug,
        title=scenario.title,
        body_markdown=scenario.body_markdown,
        author_user_id=scenario.author_user_id,
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
        live_public_slug=live_slug,
        live_public_title=live_title,
        live_public_body_markdown=live_body,
    )


@router.post("", response_model=ScenarioResponse)
async def create_scenario(
    payload: ScenarioCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SCENARIO_CREATE_DRAFT)),
) -> ScenarioResponse:
    scenario = await _service(db).create_draft(
        current_user=current_user,
        title=payload.title,
        body_markdown=payload.body_markdown,
    )
    return _to_response(scenario)


@router.get("/mine", response_model=list[ScenarioSummaryResponse])
async def list_my_scenarios(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SCENARIO_READ_OWN)),
) -> list[ScenarioSummaryResponse]:
    scenarios = await _service(db).list_my_scenarios(current_user=current_user)
    return [
        ScenarioSummaryResponse(
            id=s.id or "",
            slug=s.public_slug if s.published_at is not None else s.slug,
            title=s.title,
            state=s.state,
            updated_at=s.updated_at,
            first_published_at=s.first_published_at,
        )
        for s in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_permission(Permission.SCENARIO_READ_OWN, Permission.SCENARIO_READ_REVIEW_QUEUE)
    ),
) -> ScenarioResponse:
    scenario = await _service(db).get_scenario_if_readable(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return _to_response(scenario)


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def patch_scenario(
    scenario_id: str,
    payload: ScenarioPatchRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_any_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
    ),
) -> ScenarioResponse:
    scenario = await _service(db).patch_draft(
        scenario_id=scenario_id,
        current_user=current_user,
        title=payload.title,
        body_markdown=payload.body_markdown,
        summary=payload.summary,
        categories=payload.categories,
        tags=payload.tags,
        sensitive_data_involved=payload.sensitive_data_involved,
    )
    return _to_response(scenario)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SCENARIO_DELETE_OWN)),
) -> None:
    await _service(db).delete_draft(scenario_id=scenario_id, current_user=current_user)


@router.post("/{scenario_id}/submit-review", response_model=SubmitReviewResponse)
async def submit_review(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SCENARIO_SUBMIT_REVIEW)),
) -> SubmitReviewResponse:
    scenario = await _service(db).submit_review(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return SubmitReviewResponse(
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
        require_any_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
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
        require_any_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
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
        require_any_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
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
        require_any_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
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
        require_any_permission(Permission.SCENARIO_UPDATE_OWN, Permission.SCENARIO_UPDATE_IN_REVIEW)
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
        require_any_permission(Permission.SCENARIO_READ_OWN, Permission.SCENARIO_READ_REVIEW_QUEUE)
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
        require_any_permission(Permission.SCENARIO_READ_OWN, Permission.SCENARIO_READ_REVIEW_QUEUE)
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


@router.post("/{scenario_id}/collaborators", response_model=ScenarioResponse)
async def add_collaborator(
    scenario_id: str,
    payload: AddCollaboratorRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SCENARIO_UPDATE_OWN)),
) -> ScenarioResponse:
    scenario = await _service(db).add_editor(
        scenario_id=scenario_id,
        editor_user_id=payload.user_id,
        current_user=current_user,
    )
    return _to_response(scenario)


@router.delete("/{scenario_id}/collaborators/{user_id}", response_model=ScenarioResponse)
async def remove_collaborator(
    scenario_id: str,
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_permission(Permission.SCENARIO_UPDATE_OWN)),
) -> ScenarioResponse:
    scenario = await _service(db).remove_editor(
        scenario_id=scenario_id,
        editor_user_id=user_id,
        current_user=current_user,
    )
    return _to_response(scenario)


