"""Public routes for published scenarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api_auth import get_current_user
from app.db import get_db
from app.domain.enums import ScenarioState
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenario_comments import ScenarioCommentsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.public import (
    PublicScenarioCommentCreateRequest,
    PublicScenarioCommentResponse,
    PublicScenarioCommentsResponse,
    PublicScenarioListItem,
    PublicScenarioResponse,
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


@router.get("/scenarios", response_model=list[PublicScenarioListItem])
async def list_public_scenarios(db: AsyncIOMotorDatabase = Depends(get_db)) -> list[PublicScenarioListItem]:
    repo = ScenariosRepository(db)
    scenarios = await repo.list_by_state(state=ScenarioState.PUBLISHED)
    return [
        PublicScenarioListItem(
            id=s.id or "",
            slug=s.slug,
            title=s.title,
            published_at=s.published_at or s.updated_at,
        )
        for s in scenarios
        if s.published_at is not None
    ]


@router.get("/scenarios/{slug}", response_model=PublicScenarioResponse)
async def get_public_scenario(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> PublicScenarioResponse:
    repo = ScenariosRepository(db)
    scenario = await repo.get_by_slug_and_state(slug=slug, state=ScenarioState.PUBLISHED)
    if scenario is None or scenario.published_at is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return PublicScenarioResponse(
        id=scenario.id or "",
        slug=scenario.slug,
        title=scenario.title,
        body_markdown=scenario.body_markdown,
        published_at=scenario.published_at,
    )


@router.get("/scenarios/{slug}/comments", response_model=PublicScenarioCommentsResponse)
async def list_public_scenario_comments(slug: str, db: AsyncIOMotorDatabase = Depends(get_db)) -> PublicScenarioCommentsResponse:
    scenario, comments = await _service(db).list_public_comments_by_slug(slug=slug)
    return PublicScenarioCommentsResponse(
        scenario_id=scenario.id or "",
        slug=scenario.slug,
        items=[
            PublicScenarioCommentResponse(
                id=c.id or "",
                author_user_id=c.author_user_id,
                body_markdown=c.body_markdown,
                revision_number=c.revision_number,
                section_key=c.section_key,
                field_path=c.field_path,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in comments
        ],
    )


@router.post("/scenarios/{slug}/comments", response_model=PublicScenarioCommentResponse)
async def create_public_scenario_comment(
    slug: str,
    payload: PublicScenarioCommentCreateRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PublicScenarioCommentResponse:
    comment = await _service(db).add_public_comment_by_slug(
        slug=slug,
        current_user=current_user,
        body_markdown=payload.body_markdown,
        revision_number=payload.revision_number,
        section_key=payload.section_key,
        field_path=payload.field_path,
    )
    return PublicScenarioCommentResponse(
        id=comment.id or "",
        author_user_id=comment.author_user_id,
        body_markdown=comment.body_markdown,
        revision_number=comment.revision_number,
        section_key=comment.section_key,
        field_path=comment.field_path,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )
