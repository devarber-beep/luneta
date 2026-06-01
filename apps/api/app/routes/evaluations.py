"""Routes for ethical evaluations on published scenarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps.authz import require_active_user_with_permission
from app.domain.authz_permissions import Permission
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_evaluations import ScenarioEvaluationsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.schemas.evaluations import (
    EvaluationListResponse,
    EvaluationResponse,
    EvaluationSummaryResponse,
    ModerateEvaluationRequest,
    MyEvaluationResponse,
    SubmitEvaluationRequest,
)
from app.services.audit_service import AuditService
from app.services.evaluation_service import EvaluationService
from app.services.notifications_factory import build_notification_service

router = APIRouter()


def _service(db: AsyncIOMotorDatabase) -> EvaluationService:
    return EvaluationService(
        scenarios_repo=ScenariosRepository(db),
        evaluations_repo=ScenarioEvaluationsRepository(db),
        ethical_repo=EthicalRisksRepository(db),
        users_repo=UsersRepository(db),
        audit_service=AuditService(audit_repo=AuditEventsRepository(db)),
        notification_service=build_notification_service(db),
    )


@router.get("/{scenario_id}/evaluations/me", response_model=MyEvaluationResponse)
async def get_my_evaluation(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.USER_READ_SELF)),
) -> MyEvaluationResponse:
    service = _service(db)
    evaluation, can_submit = await service.get_my_evaluation(
        scenario_id=scenario_id,
        current_user=current_user,
    )
    include_identity = True
    eval_response = None
    if evaluation is not None:
        payload = await service.build_evaluation_response(
            evaluation,
            include_evaluator_identity=include_identity,
        )
        eval_response = EvaluationResponse(**payload)
    return MyEvaluationResponse(evaluation=eval_response, can_submit=can_submit)


@router.post("/{scenario_id}/evaluations", response_model=EvaluationResponse, status_code=201)
async def submit_evaluation(
    scenario_id: str,
    body: SubmitEvaluationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(
        require_active_user_with_permission(Permission.SCENARIO_EVALUATE_PUBLISHED)
    ),
) -> EvaluationResponse:
    service = _service(db)
    created = await service.submit_evaluation(
        scenario_id=scenario_id,
        current_user=current_user,
        risk_score=body.risk_score,
        benefit_score=body.benefit_score,
        detected_ethical_risk_ids=body.detected_ethical_risk_ids,
        comment=body.comment,
        aspects=body.aspects,
    )
    payload = await service.build_evaluation_response(created, include_evaluator_identity=True)
    return EvaluationResponse(**payload)


@router.get("/{scenario_id}/evaluations/summary", response_model=EvaluationSummaryResponse)
async def evaluation_summary(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.USER_READ_SELF)),
) -> EvaluationSummaryResponse:
    service = _service(db)
    summary = await service.get_summary(scenario_id=scenario_id, current_user=current_user)
    return EvaluationSummaryResponse(**summary)


@router.get("/{scenario_id}/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(
    scenario_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.USER_READ_SELF)),
) -> EvaluationListResponse:
    service = _service(db)
    evaluations = await service.list_detail(scenario_id=scenario_id, current_user=current_user)
    include_identity = True
    items: list[EvaluationResponse] = []
    for evaluation in evaluations:
        payload = await service.build_evaluation_response(
            evaluation,
            include_evaluator_identity=include_identity,
        )
        items.append(EvaluationResponse(**payload))
    return EvaluationListResponse(items=items)


@router.post("/evaluations/{evaluation_id}/moderate", status_code=204)
async def moderate_evaluation(
    evaluation_id: str,
    body: ModerateEvaluationRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: UserModel = Depends(require_active_user_with_permission(Permission.EVALUATION_MODERATE)),
) -> None:
    await _service(db).moderate_evaluation(
        evaluation_id=evaluation_id,
        current_user=current_user,
        action=body.action,
    )
