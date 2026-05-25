"""Admin routes for ethical evaluation moderation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_active_user_with_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.scenario_evaluations import ScenarioEvaluationsRepository
from app.repositories.scenarios import ScenariosRepository
from app.schemas.evaluations import (
    AdminEvaluationModerationTarget,
    AdminEvaluationModerationTargetsResponse,
)

router = APIRouter()


@router.get("/evaluations/moderation-targets", response_model=AdminEvaluationModerationTargetsResponse)
async def list_moderation_targets(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.EVALUATION_MODERATE)
    ),
) -> AdminEvaluationModerationTargetsResponse:
    scenarios = await ScenariosRepository(db).list_publicly_visible()
    counts = await ScenarioEvaluationsRepository(db).count_all_by_scenario_id()
    items: list[AdminEvaluationModerationTarget] = []
    for scenario in scenarios:
        sid = scenario.id or ""
        if not sid:
            continue
        published_at = scenario.published_at or scenario.updated_at
        items.append(
            AdminEvaluationModerationTarget(
                scenario_id=sid,
                title=scenario.public_title or scenario.title,
                published_at=published_at,
                evaluation_count=counts.get(sid, 0),
            )
        )
    items.sort(
        key=lambda row: (row.evaluation_count, row.published_at),
        reverse=True,
    )
    return AdminEvaluationModerationTargetsResponse(items=items)
