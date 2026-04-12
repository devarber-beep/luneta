"""Scenario routes for create/read/edit/submit-review."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api_auth import get_current_user
from app.db import get_db
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenario_comments import ScenarioCommentsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.scenarios import (
    AddCollaboratorRequest,
    ScenarioCommentCreateRequest,
    ScenarioCommentResponse,
    ScenarioCommentsResponse,
    ScenarioCreateRequest,
    ScenarioCollaboratorsResponse,
    ScenarioCollaboratorResponse,
    ScenarioPatchRequest,
    ScenarioResponse,
    ScenarioSummaryResponse,
    SubmitReviewResponse,
)
from app.services.scenario_service import ScenarioService

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> ScenarioService:
    return ScenarioService(
        scenarios_repo=ScenariosRepository(db),
        revisions_repo=ScenarioRevisionsRepository(db),
        review_events_repo=ReviewEventsRepository(db),
        comments_repo=ScenarioCommentsRepository(db),
        users_repo=UsersRepository(db),
    )


def _to_response(scenario) -> ScenarioResponse:
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
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


def _to_comment_response(comment) -> ScenarioCommentResponse:
    return ScenarioCommentResponse(
        id=comment.id or "",
        scenario_id=comment.scenario_id,
        author_user_id=comment.author_user_id,
        body_markdown=comment.body_markdown,
        revision_number=comment.revision_number,
        section_key=comment.section_key,
        field_path=comment.field_path,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.post("", response_model=ScenarioResponse)
async def create_scenario(
    payload: ScenarioCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ScenarioResponse:
    scenario = await _service(db).create_draft(
        current_user=current_user,
        slug=payload.slug,
        title=payload.title,
        body_markdown=payload.body_markdown,
    )
    return _to_response(scenario)


@router.get("/mine", response_model=list[ScenarioSummaryResponse])
async def list_my_scenarios(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ScenarioSummaryResponse]:
    scenarios = await _service(db).list_my_scenarios(current_user=current_user)
    return [
        ScenarioSummaryResponse(
            id=s.id or "",
            slug=s.slug,
            title=s.title,
            state=s.state,
            updated_at=s.updated_at,
        )
        for s in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ScenarioResponse:
    scenario = await _service(db).get_for_author_or_reviewer(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return _to_response(scenario)


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
async def patch_scenario(
    scenario_id: str,
    payload: ScenarioPatchRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ScenarioResponse:
    scenario = await _service(db).patch_draft(
        scenario_id=scenario_id,
        current_user=current_user,
        title=payload.title,
        body_markdown=payload.body_markdown,
    )
    return _to_response(scenario)


@router.post("/{scenario_id}/submit-review", response_model=SubmitReviewResponse)
async def submit_review(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SubmitReviewResponse:
    scenario = await _service(db).submit_review(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return SubmitReviewResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
    )


@router.get("/{scenario_id}/collaborators", response_model=ScenarioCollaboratorsResponse)
async def list_collaborators(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
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
    current_user=Depends(get_current_user),
) -> ScenarioResponse:
    scenario = await _service(db).remove_editor(
        scenario_id=scenario_id,
        editor_user_id=user_id,
        current_user=current_user,
    )
    return _to_response(scenario)


@router.get("/{scenario_id}/comments", response_model=ScenarioCommentsResponse)
async def list_comments(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ScenarioCommentsResponse:
    comments = await _service(db).list_comments(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    return ScenarioCommentsResponse(
        scenario_id=scenario_id,
        items=[_to_comment_response(comment) for comment in comments],
    )


@router.post("/{scenario_id}/comments", response_model=ScenarioCommentResponse)
async def create_comment(
    scenario_id: str,
    payload: ScenarioCommentCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ScenarioCommentResponse:
    comment = await _service(db).add_comment(
        scenario_id=scenario_id,
        current_user=current_user,
        body_markdown=payload.body_markdown,
        revision_number=payload.revision_number,
        section_key=payload.section_key,
        field_path=payload.field_path,
    )
    return _to_comment_response(comment)
