"""Scenario ethical evaluations repository."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.domain.enums import EvaluationVisibility
from app.models.scenario_evaluation import EvaluationAspectsModel, ScenarioEvaluationModel


class ScenarioEvaluationsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["scenario_evaluations"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index(
            [("scenario_id", 1), ("evaluator_user_id", 1)],
            unique=True,
        )
        await self._collection.create_index([("scenario_id", 1), ("visibility", 1)])

    async def create(
        self,
        *,
        scenario_id: str,
        evaluator_user_id: str,
        risk_score: float,
        benefit_score: float,
        detected_ethical_risk_ids: list[str],
        comment: str,
        aspects: EvaluationAspectsModel,
    ) -> ScenarioEvaluationModel:
        now = datetime.now(UTC)
        doc: dict[str, Any] = {
            "scenario_id": scenario_id,
            "evaluator_user_id": evaluator_user_id,
            "risk_score": risk_score,
            "benefit_score": benefit_score,
            "detected_ethical_risk_ids": list(detected_ethical_risk_ids),
            "comment": comment.strip(),
            "aspects": aspects.model_dump(mode="json"),
            "visibility": EvaluationVisibility.VISIBLE.value,
            "submitted_at": now,
            "created_at": now,
            "updated_at": now,
        }
        try:
            result = await self._collection.insert_one(doc)
        except DuplicateKeyError as exc:
            raise ValueError("evaluation_already_exists") from exc
        doc["_id"] = str(result.inserted_id)
        return ScenarioEvaluationModel.model_validate(doc)

    async def get_by_id(self, evaluation_id: str) -> ScenarioEvaluationModel | None:
        if not ObjectId.is_valid(evaluation_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(evaluation_id)})
        return self._to_model(doc)

    async def get_for_scenario_and_evaluator(
        self,
        *,
        scenario_id: str,
        evaluator_user_id: str,
    ) -> ScenarioEvaluationModel | None:
        doc = await self._collection.find_one(
            {"scenario_id": scenario_id, "evaluator_user_id": evaluator_user_id}
        )
        return self._to_model(doc)

    async def list_for_scenario(
        self,
        *,
        scenario_id: str,
        include_hidden: bool = False,
    ) -> list[ScenarioEvaluationModel]:
        query: dict[str, Any] = {"scenario_id": scenario_id}
        if not include_hidden:
            query["visibility"] = EvaluationVisibility.VISIBLE.value
        cursor = self._collection.find(query).sort("submitted_at", -1)
        out: list[ScenarioEvaluationModel] = []
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                out.append(model)
        return out

    async def set_visibility(
        self,
        *,
        evaluation_id: str,
        visibility: EvaluationVisibility,
    ) -> ScenarioEvaluationModel | None:
        if not ObjectId.is_valid(evaluation_id):
            return None
        now = datetime.now(UTC)
        doc = await self._collection.find_one_and_update(
            {"_id": ObjectId(evaluation_id)},
            {"$set": {"visibility": visibility.value, "updated_at": now}},
            return_document=True,
        )
        return self._to_model(doc)

    async def count_all_by_scenario_id(self) -> dict[str, int]:
        pipeline = [{"$group": {"_id": "$scenario_id", "count": {"$sum": 1}}}]
        counts: dict[str, int] = {}
        async for row in self._collection.aggregate(pipeline):
            scenario_id = row.get("_id")
            if isinstance(scenario_id, str) and scenario_id:
                counts[scenario_id] = int(row.get("count", 0))
        return counts

    async def delete_by_id(self, evaluation_id: str) -> bool:
        if not ObjectId.is_valid(evaluation_id):
            return False
        result = await self._collection.delete_one({"_id": ObjectId(evaluation_id)})
        return result.deleted_count > 0

    @staticmethod
    def _to_model(doc: dict[str, Any] | None) -> ScenarioEvaluationModel | None:
        if doc is None:
            return None
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return ScenarioEvaluationModel.model_validate(doc)
