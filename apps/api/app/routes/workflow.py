"""Workflow routes for reviewer queue and transitions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api_auth import get_current_user
from app.db import get_db
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenarios import ScenariosRepository
from app.schemas.workflow import ReviewQueueResponse, WorkflowActionResponse
from app.services.workflow_service import WorkflowService

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> WorkflowService:
    return WorkflowService(
        scenarios_repo=ScenariosRepository(db),
        review_events_repo=ReviewEventsRepository(db),
    )


@router.get("/review-queue", response_model=ReviewQueueResponse)
async def review_queue(
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ReviewQueueResponse:
    items = await _service(db).review_queue(current_user=current_user)
    return ReviewQueueResponse(items=items)


@router.post("/scenarios/{scenario_id}/approve", response_model=WorkflowActionResponse)
async def approve(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowActionResponse:
    scenario, changed_at = await _service(db).approve(scenario_id=scenario_id, current_user=current_user)
    return WorkflowActionResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
        changed_at=changed_at,
    )


@router.post("/scenarios/{scenario_id}/publish", response_model=WorkflowActionResponse)
async def publish(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WorkflowActionResponse:
    scenario, changed_at = await _service(db).publish(scenario_id=scenario_id, current_user=current_user)
    return WorkflowActionResponse(
        scenario_id=scenario.id or "",
        state=scenario.state,
        changed_at=changed_at,
    )
