"""Ethical evaluation service for published scenarios."""
from __future__ import annotations

from collections import Counter

from fastapi import HTTPException, status

from app.core.evaluation_access import (
    can_moderate_evaluations,
    can_read_evaluation_comments,
    can_read_evaluation_detail,
    can_read_evaluation_summary,
    can_read_own_evaluation,
    can_submit_evaluation,
)
from app.domain.enums import AuditActionType, AuditSubjectType, EvaluationVisibility
from app.models.scenario import ScenarioModel
from app.models.scenario_evaluation import EvaluationAspectsModel, ScenarioEvaluationModel
from app.models.user import UserModel
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.scenario_evaluations import ScenarioEvaluationsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.services.audit_service import AuditService


class EvaluationService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        evaluations_repo: ScenarioEvaluationsRepository,
        ethical_repo: EthicalRisksRepository,
        users_repo: UsersRepository,
        audit_service: AuditService,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._evaluations_repo = evaluations_repo
        self._ethical_repo = ethical_repo
        self._users_repo = users_repo
        self._audit = audit_service

    async def get_my_evaluation(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
    ) -> tuple[ScenarioEvaluationModel | None, bool]:
        scenario = await self._require_scenario(scenario_id)
        if not can_read_own_evaluation(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        existing = await self._evaluations_repo.get_for_scenario_and_evaluator(
            scenario_id=scenario_id,
            evaluator_user_id=current_user.id or "",
        )
        can_submit = can_submit_evaluation(user=current_user, scenario=scenario) and existing is None
        return existing, can_submit

    async def submit_evaluation(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        risk_score: float,
        benefit_score: float,
        detected_ethical_risk_ids: list[str],
        comment: str,
        aspects: EvaluationAspectsModel,
    ) -> ScenarioEvaluationModel:
        scenario = await self._require_scenario(scenario_id)
        if not can_submit_evaluation(user=current_user, scenario=scenario):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot evaluate this scenario",
            )
        await self._validate_ethical_risk_ids(detected_ethical_risk_ids)
        existing = await self._evaluations_repo.get_for_scenario_and_evaluator(
            scenario_id=scenario_id,
            evaluator_user_id=current_user.id or "",
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already submitted an evaluation for this scenario",
            )
        await self._evaluations_repo.ensure_indexes()
        try:
            created = await self._evaluations_repo.create(
                scenario_id=scenario_id,
                evaluator_user_id=current_user.id or "",
                risk_score=risk_score,
                benefit_score=benefit_score,
                detected_ethical_risk_ids=detected_ethical_risk_ids,
                comment=comment,
                aspects=aspects,
            )
        except ValueError as exc:
            if str(exc) == "evaluation_already_exists":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You already submitted an evaluation for this scenario",
                ) from exc
            raise
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.EVALUATION_SUBMITTED,
            subject_type=AuditSubjectType.EVALUATION,
            subject_id=created.id or "",
            current={
                "scenario_id": scenario_id,
                "evaluator_user_id": current_user.id,
                "risk_score": risk_score,
                "benefit_score": benefit_score,
            },
        )
        return created

    async def get_summary(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
    ) -> dict:
        scenario = await self._require_scenario(scenario_id)
        if not can_read_evaluation_summary(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        evaluations = await self._evaluations_repo.list_for_scenario(
            scenario_id=scenario_id,
            include_hidden=False,
        )
        include_comments = can_read_evaluation_comments(user=current_user, scenario=scenario)
        return await self._build_summary(
            scenario_id=scenario_id,
            evaluations=evaluations,
            include_comments=include_comments,
        )

    async def list_detail(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
    ) -> list[ScenarioEvaluationModel]:
        scenario = await self._require_scenario(scenario_id)
        if not can_read_evaluation_detail(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        include_hidden = can_moderate_evaluations(user=current_user)
        return await self._evaluations_repo.list_for_scenario(
            scenario_id=scenario_id,
            include_hidden=include_hidden,
        )

    async def moderate_evaluation(
        self,
        *,
        evaluation_id: str,
        current_user: UserModel,
        action: str,
    ) -> None:
        if not can_moderate_evaluations(user=current_user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        evaluation = await self._evaluations_repo.get_by_id(evaluation_id)
        if evaluation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
        normalized = action.strip().lower()
        if normalized == "hide":
            updated = await self._evaluations_repo.set_visibility(
                evaluation_id=evaluation_id,
                visibility=EvaluationVisibility.HIDDEN,
            )
            if updated is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
            await self._audit.record(
                actor=current_user,
                action_type=AuditActionType.EVALUATION_MODERATED,
                subject_type=AuditSubjectType.EVALUATION,
                subject_id=evaluation_id,
                previous={"visibility": evaluation.visibility.value},
                current={"visibility": EvaluationVisibility.HIDDEN.value, "action": "hide"},
            )
            return
        if normalized == "delete":
            await self._evaluations_repo.delete_by_id(evaluation_id)
            await self._audit.record(
                actor=current_user,
                action_type=AuditActionType.EVALUATION_MODERATED,
                subject_type=AuditSubjectType.EVALUATION,
                subject_id=evaluation_id,
                previous={"scenario_id": evaluation.scenario_id},
                current={"action": "delete"},
            )
            return
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action must be hide or delete")

    async def build_evaluation_response(
        self,
        evaluation: ScenarioEvaluationModel,
        *,
        include_evaluator_identity: bool,
    ) -> dict:
        labels = await self._labels_for_risk_ids(evaluation.detected_ethical_risk_ids)
        evaluator_nickname: str | None = None
        if include_evaluator_identity:
            evaluator = await self._users_repo.get_by_id(evaluation.evaluator_user_id)
            if evaluator is not None:
                evaluator_nickname = evaluator.nickname
        return {
            "id": evaluation.id or "",
            "scenario_id": evaluation.scenario_id,
            "evaluator_user_id": evaluation.evaluator_user_id if include_evaluator_identity else "",
            "evaluator_nickname": evaluator_nickname,
            "risk_score": evaluation.risk_score,
            "benefit_score": evaluation.benefit_score,
            "detected_ethical_risk_ids": evaluation.detected_ethical_risk_ids,
            "detected_ethical_risk_labels": labels,
            "comment": evaluation.comment,
            "aspects": evaluation.aspects.model_dump(mode="json"),
            "visibility": evaluation.visibility,
            "submitted_at": evaluation.submitted_at,
        }

    async def _build_summary(
        self,
        *,
        scenario_id: str,
        evaluations: list[ScenarioEvaluationModel],
        include_comments: bool = False,
    ) -> dict:
        if not evaluations:
            return {
                "scenario_id": scenario_id,
                "evaluation_count": 0,
                "average_risk_score": None,
                "average_benefit_score": None,
                "detected_ethical_risk_labels": [],
                "comments": [],
            }
        risk_sum = sum(e.risk_score for e in evaluations)
        benefit_sum = sum(e.benefit_score for e in evaluations)
        label_counter: Counter[str] = Counter()
        for evaluation in evaluations:
            for label in await self._labels_for_risk_ids(evaluation.detected_ethical_risk_ids):
                label_counter[label] += 1
        top_labels = [label for label, _ in label_counter.most_common()]
        count = len(evaluations)
        comments: list[str] = []
        if include_comments:
            comments = [e.comment.strip() for e in evaluations if e.comment.strip()]
        return {
            "scenario_id": scenario_id,
            "evaluation_count": count,
            "average_risk_score": round(risk_sum / count, 2),
            "average_benefit_score": round(benefit_sum / count, 2),
            "detected_ethical_risk_labels": top_labels,
            "comments": comments,
        }

    async def _validate_ethical_risk_ids(self, risk_ids: list[str]) -> None:
        active = {e.id for e in await self._ethical_repo.list_active() if e.id}
        for risk_id in risk_ids:
            if risk_id not in active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or inactive ethical risk selection",
                )

    async def _labels_for_risk_ids(self, risk_ids: list[str]) -> list[str]:
        labels: list[str] = []
        for risk_id in risk_ids:
            entry = await self._ethical_repo.get_by_id(risk_id)
            if entry is not None:
                labels.append(entry.label)
        return labels

    async def _require_scenario(self, scenario_id: str) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return scenario
