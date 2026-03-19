"""Scenario routes for create/read/edit/submit-review."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api_auth import get_current_user
from app.db import get_db
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.schemas.scenarios import (
    ScenarioCreateRequest,
    ScenarioPatchRequest,
    ScenarioResponse,
    SubmitReviewResponse,
)
from app.services.scenario_service import ScenarioService

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> ScenarioService:
    return ScenarioService(
        scenarios_repo=ScenariosRepository(db),
        revisions_repo=ScenarioRevisionsRepository(db),
        review_events_repo=ReviewEventsRepository(db),
    )


def _to_response(scenario) -> ScenarioResponse:
    return ScenarioResponse(
        id=scenario.id or "",
        slug=scenario.slug,
        title=scenario.title,
        body_markdown=scenario.body_markdown,
        author_user_id=scenario.author_user_id,
        state=scenario.state,
        current_revision_number=scenario.current_revision_number,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
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
