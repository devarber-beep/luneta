"""Scenario repository."""
from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums import CollaboratorRole, ReviewOutcome, ScenarioState
from app.models.scenario import ScenarioModel, slugify_title


class ScenariosRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["scenarios"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index(
            [("slug", 1)],
            unique=True,
            partialFilterExpression={"slug": {"$type": "string"}},
        )
        await self._collection.create_index(
            [("public_slug", 1)],
            unique=True,
            partialFilterExpression={"public_slug": {"$type": "string"}},
        )
        await self._collection.create_index("author_user_id")
        await self._collection.create_index("collaborators.user_id")
        await self._collection.create_index("state")
        await self._collection.create_index([("published_at", -1)])

    async def create(
        self,
        *,
        title: str,
        description: str,
        author_user_id: str,
    ) -> ScenarioModel:
        now = datetime.now(UTC)
        slug = await self._allocate_unique_slug(title=title)
        doc = {
            "slug": slug,
            "title": title,
            "description": description,
            "category_ids": [],
            "ethical_risk_ids": [],
            "author_user_id": author_user_id,
            "collaborators": [
                {
                    "user_id": author_user_id,
                    "role": CollaboratorRole.OWNER.value,
                    "added_at": now,
                    "added_by": author_user_id,
                }
            ],
            "state": ScenarioState.DRAFT.value,
            "current_revision_number": 1,
            "summary": None,
            "categories": [],
            "tags": [],
            "keywords_normalized": [],
            "cover_image": None,
            "inline_assets": [],
            "ethical_considerations": None,
            "risk_assessment": None,
            "sensitive_data_involved": None,
            "avg_rating": None,
            "rating_count": 0,
            "rating_sum": 0,
            "favorites_count": 0,
            "archived_at": None,
            "deleted_at": None,
            "submitted_for_review_at": None,
            "submitted_for_review_by_user_id": None,
            "review_started_at": None,
            "review_feedback_note": None,
            "review_feedback_at": None,
            "review_feedback_by_user_id": None,
            "not_suitable_reason": None,
            "not_suitable_at": None,
            "not_suitable_by_user_id": None,
            "last_reviewed_at": None,
            "last_reviewed_by_user_id": None,
            "last_review_outcome": None,
            "approved_at": None,
            "first_approved_at": None,
            "approved_by_user_id": None,
            "published_at": None,
            "first_published_at": None,
            "published_by_user_id": None,
            "public_revision_number": None,
            "last_state_changed_at": now,
            "created_at": now,
            "updated_at": now,
        }
        result = await self._collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return ScenarioModel.model_validate(doc)

    async def get_by_id(self, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        doc = await self._collection.find_one({"_id": ObjectId(scenario_id), "deleted_at": None})
        return self._to_model(doc)

    async def get_by_public_slug(self, slug: str) -> ScenarioModel | None:
        doc = await self._collection.find_one({"public_slug": slug, "deleted_at": None})
        return self._to_model(doc)

    async def update_draft_content(
        self,
        *,
        scenario_id: str,
        title: str | None,
        description: str | None,
        summary: str | None,
        categories: list[str] | None,
        tags: list[str] | None,
        category_ids: list[str] | None = None,
        ethical_risk_ids: list[str] | None = None,
        sensitive_data_involved: bool | None = None,
    ) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        set_doc: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if title is not None:
            set_doc["title"] = title
            set_doc["slug"] = await self._allocate_unique_slug(title=title, exclude_id=scenario_id)
        if description is not None:
            set_doc["description"] = description
        if category_ids is not None:
            set_doc["category_ids"] = category_ids
        if ethical_risk_ids is not None:
            set_doc["ethical_risk_ids"] = ethical_risk_ids
        if summary is not None:
            set_doc["summary"] = summary
        if categories is not None:
            set_doc["categories"] = categories
        if tags is not None:
            set_doc["tags"] = tags
        if sensitive_data_involved is not None:
            set_doc["sensitive_data_involved"] = sensitive_data_involved
        if any(k in set_doc for k in {"title", "summary", "categories", "tags"}):
            existing = await self.get_by_id(scenario_id)
            if existing is not None:
                kw_title = set_doc.get("title", existing.title)
                kw_summary = set_doc.get("summary", existing.summary)
                kw_categories = set_doc.get("categories", existing.categories)
                kw_tags = set_doc.get("tags", existing.tags)
                set_doc["keywords_normalized"] = self._build_keywords(
                    title=kw_title,
                    summary=kw_summary,
                    categories=kw_categories,
                    tags=kw_tags,
                )
        if len(set_doc) == 1:
            return await self.get_by_id(scenario_id)
        await self._collection.update_one({"_id": ObjectId(scenario_id)}, {"$set": set_doc})
        return await self.get_by_id(scenario_id)

    async def set_cover_image(self, *, scenario_id: str, asset: dict[str, Any]) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$set": {"cover_image": asset, "updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def clear_cover_image(self, *, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$set": {"cover_image": None, "updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def add_inline_image(self, *, scenario_id: str, asset: dict[str, Any]) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$push": {"inline_assets": asset}, "$set": {"updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def remove_inline_image(self, *, scenario_id: str, asset_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$pull": {"inline_assets": {"asset_id": asset_id}}, "$set": {"updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def replace_inline_assets(self, *, scenario_id: str, assets: list[dict[str, Any]]) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$set": {"inline_assets": assets, "updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def submit_to_queue(self, *, scenario_id: str, actor_user_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {
                "$set": {
                    "state": ScenarioState.QUEUED.value,
                    "submitted_for_review_at": now,
                    "submitted_for_review_by_user_id": actor_user_id,
                    "review_started_at": None,
                    "last_state_changed_at": now,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(scenario_id)

    async def start_review(self, *, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {
                "$set": {
                    "state": ScenarioState.IN_REVIEW.value,
                    "review_started_at": now,
                    "last_state_changed_at": now,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(scenario_id)

    async def request_changes(
        self,
        *,
        scenario_id: str,
        reviewer_user_id: str,
        note: str,
    ) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {
                "$set": {
                    "state": ScenarioState.CHANGES_REQUIRED.value,
                    "review_feedback_note": note,
                    "review_feedback_at": now,
                    "review_feedback_by_user_id": reviewer_user_id,
                    "last_reviewed_at": now,
                    "last_reviewed_by_user_id": reviewer_user_id,
                    "last_review_outcome": ReviewOutcome.CHANGES_REQUIRED.value,
                    "last_state_changed_at": now,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(scenario_id)

    async def mark_not_suitable(
        self,
        *,
        scenario_id: str,
        reviewer_user_id: str,
        reason: str | None,
    ) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {
                "$set": {
                    "state": ScenarioState.NOT_SUITABLE.value,
                    "not_suitable_reason": reason,
                    "not_suitable_at": now,
                    "not_suitable_by_user_id": reviewer_user_id,
                    "last_reviewed_at": now,
                    "last_reviewed_by_user_id": reviewer_user_id,
                    "last_review_outcome": ReviewOutcome.NOT_SUITABLE.value,
                    "last_state_changed_at": now,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(scenario_id)

    async def open_working_copy_from_published(self, *, scenario_id: str) -> ScenarioModel | None:
        """Move a published scenario into draft so the owner can edit a working copy."""
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id), "state": ScenarioState.PUBLISHED.value},
            {
                "$set": {
                    "state": ScenarioState.DRAFT.value,
                    "last_state_changed_at": now,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(scenario_id)

    async def start_applying_changes(self, *, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {
                "$set": {
                    "state": ScenarioState.APPLYING_CHANGES.value,
                    "last_state_changed_at": now,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(scenario_id)

    async def reopen_from_not_suitable(self, *, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {
                "$set": {
                    "state": ScenarioState.DRAFT.value,
                    "not_suitable_reason": None,
                    "not_suitable_at": None,
                    "not_suitable_by_user_id": None,
                    "submitted_for_review_at": None,
                    "submitted_for_review_by_user_id": None,
                    "review_started_at": None,
                    "last_state_changed_at": now,
                    "updated_at": now,
                }
            },
        )
        return await self.get_by_id(scenario_id)

    async def set_state(self, *, scenario_id: str, state: ScenarioState, actor_user_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        oid = ObjectId(scenario_id)
        now = datetime.now(UTC)
        if state == ScenarioState.PUBLISHED:
            await self._collection.update_one(
                {"_id": oid},
                [
                    {
                        "$set": {
                            "state": ScenarioState.PUBLISHED.value,
                            "published_at": now,
                            "published_by_user_id": actor_user_id,
                            "approved_at": now,
                            "approved_by_user_id": actor_user_id,
                            "public_revision_number": "$current_revision_number",
                            "last_state_changed_at": now,
                            "updated_at": now,
                            "public_title": "$title",
                            "public_description": "$description",
                            "public_slug": "$slug",
                            "last_reviewed_at": now,
                            "last_reviewed_by_user_id": actor_user_id,
                            "last_review_outcome": ReviewOutcome.PUBLISHED.value,
                        }
                    }
                ],
            )
            await self._collection.update_one(
                {"_id": oid, "first_published_at": None},
                {"$set": {"first_published_at": now}},
            )
            await self._collection.update_one(
                {"_id": oid, "first_approved_at": None},
                {"$set": {"first_approved_at": now}},
            )
            return await self.get_by_id(scenario_id)
        set_doc: dict[str, Any] = {"state": state.value, "last_state_changed_at": now, "updated_at": now}
        await self._collection.update_one({"_id": oid}, {"$set": set_doc})
        return await self.get_by_id(scenario_id)

    async def bump_revision_number(self, *, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$inc": {"current_revision_number": 1}, "$set": {"updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def replace_collaborators(
        self,
        *,
        scenario_id: str,
        collaborators: list[dict[str, Any]],
    ) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id)},
            {"$set": {"collaborators": collaborators, "updated_at": datetime.now(UTC)}},
        )
        return await self.get_by_id(scenario_id)

    async def soft_delete_draft(self, *, scenario_id: str) -> ScenarioModel | None:
        if not ObjectId.is_valid(scenario_id):
            return None
        now = datetime.now(UTC)
        await self._collection.update_one(
            {"_id": ObjectId(scenario_id), "state": ScenarioState.DRAFT.value, "deleted_at": None},
            {"$set": {"deleted_at": now, "updated_at": now}},
        )
        return await self.get_by_id(scenario_id)

    async def list_by_state(self, *, state: ScenarioState) -> list[ScenarioModel]:
        return await self.list_by_states(states=[state])

    async def list_by_states(
        self,
        *,
        states: list[ScenarioState],
        author_user_id: str | None = None,
        submitted_from: datetime | None = None,
        submitted_to: datetime | None = None,
    ) -> list[ScenarioModel]:
        query: dict[str, Any] = {
            "state": {"$in": [s.value for s in states]},
            "deleted_at": None,
        }
        if author_user_id:
            query["author_user_id"] = author_user_id
        if submitted_from is not None or submitted_to is not None:
            date_clause: dict[str, Any] = {}
            if submitted_from is not None:
                date_clause["$gte"] = submitted_from
            if submitted_to is not None:
                date_clause["$lte"] = submitted_to
            query["submitted_for_review_at"] = date_clause
        items: list[ScenarioModel] = []
        cursor = self._collection.find(query).sort("submitted_for_review_at", -1)
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items

    async def list_reviewed(
        self,
        *,
        reviewer_user_id: str | None = None,
        author_user_id: str | None = None,
        submitted_from: datetime | None = None,
        submitted_to: datetime | None = None,
    ) -> list[ScenarioModel]:
        query: dict[str, Any] = {
            "deleted_at": None,
            "last_reviewed_at": {"$ne": None},
            "state": {
                "$in": [
                    ScenarioState.PUBLISHED.value,
                    ScenarioState.CHANGES_REQUIRED.value,
                    ScenarioState.NOT_SUITABLE.value,
                ]
            },
        }
        if reviewer_user_id:
            query["last_reviewed_by_user_id"] = reviewer_user_id
        if author_user_id:
            query["author_user_id"] = author_user_id
        if submitted_from is not None or submitted_to is not None:
            date_clause: dict[str, Any] = {}
            if submitted_from is not None:
                date_clause["$gte"] = submitted_from
            if submitted_to is not None:
                date_clause["$lte"] = submitted_to
            query["last_reviewed_at"] = date_clause
        items: list[ScenarioModel] = []
        cursor = self._collection.find(query).sort("last_reviewed_at", -1)
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items

    @staticmethod
    def _published_visibility_filter() -> dict[str, Any]:
        return {
            "published_at": {"$ne": None},
            "deleted_at": None,
            "state": {"$ne": ScenarioState.NOT_SUITABLE.value},
            "public_slug": {"$type": "string"},
            "public_title": {"$type": "string"},
            "public_description": {"$type": "string"},
        }

    async def list_publicly_visible(self) -> list[ScenarioModel]:
        items, _total = await self.search_publicly_visible(page=1, page_size=10_000)
        return items

    async def search_publicly_visible(
        self,
        *,
        q: str | None = None,
        q_matching_author_user_ids: list[str] | None = None,
        author_user_id: str | None = None,
        published_from: datetime | None = None,
        published_to: datetime | None = None,
        category_ids: list[str] | None = None,
        ethical_risk_ids: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ScenarioModel], int]:
        clauses: list[dict[str, Any]] = [self._published_visibility_filter()]
        trimmed_q = (q or "").strip()
        if trimmed_q:
            pattern = re.escape(trimmed_q)
            text_or: list[dict[str, Any]] = [
                {"public_title": {"$regex": pattern, "$options": "i"}},
                {"public_description": {"$regex": pattern, "$options": "i"}},
                {"summary": {"$regex": pattern, "$options": "i"}},
            ]
            tokens = self._search_tokens(trimmed_q)
            if tokens:
                text_or.append({"keywords_normalized": {"$in": tokens}})
            if q_matching_author_user_ids:
                text_or.append({"author_user_id": {"$in": list(q_matching_author_user_ids)}})
            clauses.append({"$or": text_or})
        if author_user_id:
            clauses.append({"author_user_id": author_user_id})
        if published_from is not None:
            clauses.append({"published_at": {"$gte": published_from}})
        if published_to is not None:
            clauses.append({"published_at": {"$lte": published_to}})
        if category_ids:
            clauses.append({"category_ids": {"$in": list(category_ids)}})
        if ethical_risk_ids:
            clauses.append({"ethical_risk_ids": {"$in": list(ethical_risk_ids)}})
        query: dict[str, Any] = {"$and": clauses} if len(clauses) > 1 else clauses[0]
        total = await self._collection.count_documents(query)
        skip = max(page - 1, 0) * page_size
        items: list[ScenarioModel] = []
        cursor = (
            self._collection.find(query)
            .sort("published_at", -1)
            .skip(skip)
            .limit(page_size)
        )
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items, int(total)

    @staticmethod
    def _search_tokens(q: str) -> list[str]:
        tokens: list[str] = []
        for token in re.split(r"\W+", q.lower()):
            tok = token.strip()
            if len(tok) >= 2:
                tokens.append(tok)
        return list(dict.fromkeys(tokens))

    async def list_for_participating_user(self, *, user_id: str) -> list[ScenarioModel]:
        """Scenarios where the user is author or listed as collaborator."""
        query = {
            "$and": [
                {"deleted_at": None},
                {
                    "$or": [
                        {"author_user_id": user_id},
                        {"collaborators.user_id": user_id},
                    ]
                },
            ]
        }
        items: list[ScenarioModel] = []
        cursor = self._collection.find(query).sort("updated_at", -1)
        async for doc in cursor:
            model = self._to_model(doc)
            if model is not None:
                items.append(model)
        return items

    def _to_model(self, doc: dict[str, Any] | None) -> ScenarioModel | None:
        if doc is None:
            return None
        doc["_id"] = str(doc["_id"])
        return ScenarioModel.model_validate(doc)

    async def _allocate_unique_slug(self, *, title: str, exclude_id: str | None = None) -> str:
        base = slugify_title(title)[:80]
        candidate = base
        suffix = 2
        while await self._slug_exists(candidate, exclude_id=exclude_id):
            candidate = f"{base[:72]}-{suffix}"
            suffix += 1
        return candidate

    async def _slug_exists(self, slug: str, *, exclude_id: str | None = None) -> bool:
        clauses: list[dict[str, Any]] = [
            {"$or": [{"slug": slug}, {"public_slug": slug}]},
            {"deleted_at": None},
        ]
        if exclude_id and ObjectId.is_valid(exclude_id):
            clauses.append({"_id": {"$ne": ObjectId(exclude_id)}})
        return await self._collection.find_one({"$and": clauses}) is not None

    def _build_keywords(
        self,
        *,
        title: str,
        summary: str | None,
        categories: list[str],
        tags: list[str],
    ) -> list[str]:
        tokens: list[str] = []
        source = [title, summary or "", *categories, *tags]
        for piece in source:
            for token in re.split(r"\W+", piece.lower()):
                tok = token.strip()
                if len(tok) >= 2:
                    tokens.append(tok)
        # Stable order while removing duplicates.
        return list(dict.fromkeys(tokens))
