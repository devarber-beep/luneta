"""Scenario service for draft/edit/submit flow."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.permissions import (
    has_republication_pending,
    is_valid_transition,
)
from app.core.scenario_access import (
    can_admin_delete_scenario,
    can_delete_own_scenario,
    can_read_scenario,
    can_start_applying_changes_scenario,
    can_start_editing_working_copy,
    can_submit_review,
    can_update_scenario,
)
from app.domain.enums import AuditActionType, ReviewEventType, ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.scenario_usage_context import ScenarioUsageContextModel
from app.models.user import UserModel
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.services.audit_helpers import record_revision_snapshot_audit, record_scenario_audit
from app.services.audit_service import AuditService
from app.services.portfolio_loader import portfolio_investigator_ids_for_user
from app.services.notification_service import NotificationService
from app.services.content_policy import SimilarityAdvisory, enforce_content_policies
from app.services.scenario_similarity_service import ScenarioSimilarityService
from app.services.scenario_submit_validation import ensure_ready_for_submit, resolve_catalog_ids_for_save
from app.storage.minio_storage import MinioScenarioStorage


@dataclass(frozen=True)
class ScenarioSaveResult:
    scenario: ScenarioModel
    similarity_advisory: SimilarityAdvisory | None = None


class ScenarioService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        revisions_repo: ScenarioRevisionsRepository,
        review_events_repo: ReviewEventsRepository,
        users_repo: UsersRepository,
        assignments_repo: ReviewerAssignmentsRepository,
        classification_repo: ScenarioClassificationRepository,
        ethical_repo: EthicalRisksRepository,
        audit_service: AuditService | None = None,
        similarity_service: ScenarioSimilarityService | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._revisions_repo = revisions_repo
        self._review_events_repo = review_events_repo
        self._users_repo = users_repo
        self._assignments_repo = assignments_repo
        self._classification_repo = classification_repo
        self._ethical_repo = ethical_repo
        self._audit = audit_service
        self._similarity = similarity_service
        self._notifications = notification_service

    async def _portfolio_for(self, user: UserModel) -> frozenset[str]:
        return await portfolio_investigator_ids_for_user(
            user=user,
            assignments_repo=self._assignments_repo,
        )

    async def create_draft(
        self,
        *,
        current_user: UserModel,
        title: str,
        description: str,
    ) -> ScenarioSaveResult:
        await self._scenarios_repo.ensure_indexes()
        await self._revisions_repo.ensure_indexes()
        await self._review_events_repo.ensure_indexes()

        desc = description.strip()
        if len(desc) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Description is required",
            )

        scenario = await self._scenarios_repo.create(
            title=title,
            description=desc,
            author_user_id=current_user.id or "",
            author_display_name=current_user.display_name,
            author_display_name_normalized=current_user.display_name_normalized,
            author_university=current_user.university,
            author_university_normalized=current_user.university_normalized,
        )
        await self._revisions_repo.create_snapshot(
            scenario_id=scenario.id or "",
            revision_number=scenario.current_revision_number,
            title=scenario.title,
            description=scenario.description,
            state_snapshot=scenario.state,
            created_by_user_id=current_user.id or "",
        )
        await record_revision_snapshot_audit(
            self._audit,
            actor=current_user,
            scenario_id=scenario.id or "",
            revision_number=scenario.current_revision_number,
        )
        await self._review_events_repo.create(
            scenario_id=scenario.id or "",
            event_type=ReviewEventType.CREATE_DRAFT,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
            to_state=scenario.state,
        )
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_CREATED,
            scenario_id=scenario.id or "",
            to_state=scenario.state,
        )
        advisory: SimilarityAdvisory | None = None
        if self._similarity is not None:
            advisory = await enforce_content_policies(
                scenario=scenario,
                current_user=current_user,
                audit=self._audit,
                similarity=self._similarity,
                action="save",
            )
        return ScenarioSaveResult(scenario=scenario, similarity_advisory=advisory)

    async def list_my_scenarios(
        self,
        *,
        current_user: UserModel,
        q: str | None = None,
        state: ScenarioState | None = None,
        scenario_ids: list[str] | None = None,
    ) -> list[ScenarioModel]:
        await self._scenarios_repo.ensure_indexes()
        author_ids_from_name: list[str] | None = None
        trimmed_q = (q or "").strip()
        if trimmed_q:
            author_ids_from_name = await self._users_repo.list_ids_matching_display_name(trimmed_q)
        return await self._scenarios_repo.list_for_participating_user(
            user_id=current_user.id or "",
            q=q,
            q_matching_author_user_ids=author_ids_from_name or None,
            state=state,
            scenario_ids=scenario_ids,
        )

    async def get_scenario_if_readable(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        portfolio = await self._portfolio_for(current_user)
        if not can_read_scenario(
            user=current_user, scenario=scenario, portfolio_investigator_ids=portfolio
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return scenario

    async def patch_draft(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        title: str | None = None,
        description: str | None = None,
        category_ids: list[str] | None = None,
        ethical_risk_ids: list[str] | None = None,
        usage_context: ScenarioUsageContextModel | None = None,
    ) -> ScenarioSaveResult:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        portfolio = await self._portfolio_for(current_user)
        if not can_update_scenario(
            user=current_user, scenario=scenario, portfolio_investigator_ids=portfolio
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit this scenario")

        prior_state = scenario.state
        if description is not None and not description.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Description cannot be empty",
            )

        category_ids, ethical_risk_ids = await resolve_catalog_ids_for_save(
            scenario=scenario,
            category_ids=category_ids,
            ethical_risk_ids=ethical_risk_ids,
            classification_repo=self._classification_repo,
            ethical_repo=self._ethical_repo,
        )

        advisory: SimilarityAdvisory | None = None
        if self._similarity is not None:
            advisory = await enforce_content_policies(
                scenario=scenario,
                current_user=current_user,
                audit=self._audit,
                similarity=self._similarity,
                action="save",
                title=title,
                description=description,
            )

        updated = await self._scenarios_repo.update_draft_content(
            scenario_id=scenario_id,
            title=title,
            description=description.strip() if description is not None else None,
            category_ids=category_ids,
            ethical_risk_ids=ethical_risk_ids,
            usage_context=usage_context.model_dump(mode="json") if usage_context is not None else None,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        bumped = await self._scenarios_repo.bump_revision_number(scenario_id=scenario_id)
        if bumped is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        await self._revisions_repo.create_snapshot(
            scenario_id=bumped.id or "",
            revision_number=bumped.current_revision_number,
            title=bumped.title,
            description=bumped.description,
            state_snapshot=bumped.state,
            created_by_user_id=actor_user_id,
        )
        await record_revision_snapshot_audit(
            self._audit,
            actor=current_user,
            scenario_id=bumped.id or "",
            revision_number=bumped.current_revision_number,
        )
        event_type = (
            ReviewEventType.UPDATE_IN_REVIEW
            if prior_state == ScenarioState.IN_REVIEW
            else ReviewEventType.DRAFT_SAVED
        )
        await self._review_events_repo.create(
            scenario_id=bumped.id or "",
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_role=UserRole(current_user.role),
            from_state=prior_state,
            to_state=bumped.state,
        )
        changed_fields: list[str] = []
        if title is not None:
            changed_fields.append("title")
        if description is not None:
            changed_fields.append("description")
        if category_ids is not None:
            changed_fields.append("category_ids")
        if ethical_risk_ids is not None:
            changed_fields.append("ethical_risk_ids")
        if usage_context is not None:
            changed_fields.append("usage_context")
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_CONTENT_UPDATED,
            scenario_id=bumped.id or "",
            from_state=prior_state,
            to_state=bumped.state,
            current_extra={
                "revision_number": bumped.current_revision_number,
                "changed_fields": changed_fields,
                "review_event_type": event_type.value,
            },
        )
        return ScenarioSaveResult(scenario=bumped, similarity_advisory=advisory)

    async def upload_cover_image(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        storage: MinioScenarioStorage,
        content: bytes,
        content_type: str,
        alt_text: str | None,
    ) -> ScenarioModel:
        scenario = await self._get_editable_for_assets(scenario_id=scenario_id, current_user=current_user)
        storage.ensure_bucket()
        asset = storage.upload_image(
            scenario_id=scenario_id,
            scope="cover",
            content=content,
            content_type=content_type,
            alt_text=alt_text,
            order=0,
        )
        updated = await self._scenarios_repo.set_cover_image(scenario_id=scenario_id, asset=asset.model_dump())
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return updated

    async def upload_inline_image(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        storage: MinioScenarioStorage,
        content: bytes,
        content_type: str,
        alt_text: str | None,
        order: int,
    ) -> ScenarioModel:
        scenario = await self._get_editable_for_assets(scenario_id=scenario_id, current_user=current_user)
        storage.ensure_bucket()
        asset = storage.upload_image(
            scenario_id=scenario_id,
            scope="inline",
            content=content,
            content_type=content_type,
            alt_text=alt_text,
            order=order,
        )
        updated = await self._scenarios_repo.add_inline_image(scenario_id=scenario_id, asset=asset.model_dump())
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return updated

    async def remove_inline_image(
        self,
        *,
        scenario_id: str,
        asset_id: str,
        current_user: UserModel,
        storage: MinioScenarioStorage,
    ) -> ScenarioModel:
        scenario = await self._get_editable_for_assets(scenario_id=scenario_id, current_user=current_user)
        target = next((a for a in scenario.inline_assets if a.asset_id == asset_id), None)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inline asset not found")
        storage.ensure_bucket()
        storage.delete_object(storage_key=target.storage_key)
        updated = await self._scenarios_repo.remove_inline_image(scenario_id=scenario_id, asset_id=asset_id)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        # Re-compact order sequence.
        assets = [a.model_dump() for a in sorted(updated.inline_assets, key=lambda x: x.order)]
        for idx, asset in enumerate(assets):
            asset["order"] = idx
        repacked = await self._scenarios_repo.replace_inline_assets(scenario_id=scenario_id, assets=assets)
        if repacked is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return repacked

    async def remove_cover_image(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        storage: MinioScenarioStorage,
    ) -> ScenarioModel:
        scenario = await self._get_editable_for_assets(scenario_id=scenario_id, current_user=current_user)
        if scenario.cover_image is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover image not found")
        storage.ensure_bucket()
        storage.delete_object(storage_key=scenario.cover_image.storage_key)
        updated = await self._scenarios_repo.clear_cover_image(scenario_id=scenario_id)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return updated

    async def reorder_inline_images(
        self,
        *,
        scenario_id: str,
        asset_ids: list[str],
        current_user: UserModel,
    ) -> ScenarioModel:
        scenario = await self._get_editable_for_assets(scenario_id=scenario_id, current_user=current_user)
        current = {a.asset_id: a.model_dump() for a in scenario.inline_assets}
        if set(asset_ids) != set(current.keys()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="asset_ids must contain exactly all existing inline asset ids",
            )
        reordered: list[dict] = []
        for idx, asset_id in enumerate(asset_ids):
            row = current[asset_id]
            row["order"] = idx
            reordered.append(row)
        updated = await self._scenarios_repo.replace_inline_assets(scenario_id=scenario_id, assets=reordered)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return updated

    async def resolve_asset_read_url(
        self,
        *,
        scenario_id: str,
        asset_id: str,
        current_user: UserModel,
        storage: MinioScenarioStorage,
        expires_in_seconds: int = 900,
    ) -> tuple[str, int]:
        scenario = await self.get_scenario_if_readable(scenario_id=scenario_id, current_user=current_user)
        target = None
        if scenario.cover_image is not None and scenario.cover_image.asset_id == asset_id:
            target = scenario.cover_image
        if target is None:
            target = next((a for a in scenario.inline_assets if a.asset_id == asset_id), None)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        storage.ensure_bucket()
        exp = max(60, min(expires_in_seconds, 3600))
        return storage.presigned_get_url(storage_key=target.storage_key, expires_seconds=exp), exp

    async def submit_review(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        if not can_submit_review(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit this scenario")

        if not is_valid_transition(scenario.state, ScenarioState.QUEUED):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")

        if scenario.state == ScenarioState.PUBLISHED:
            if not has_republication_pending(scenario=scenario):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No changes to submit for republication",
                )

        category_ids, ethical_risk_ids = await resolve_catalog_ids_for_save(
            scenario=scenario,
            category_ids=None,
            ethical_risk_ids=None,
            classification_repo=self._classification_repo,
            ethical_repo=self._ethical_repo,
        )
        if category_ids is not None or ethical_risk_ids is not None:
            stripped = await self._scenarios_repo.update_draft_content(
                scenario_id=scenario_id,
                title=None,
                description=None,
                category_ids=category_ids,
                ethical_risk_ids=ethical_risk_ids,
            )
            if stripped is not None:
                scenario = stripped

        await ensure_ready_for_submit(
            scenario=scenario,
            classification_repo=self._classification_repo,
            ethical_repo=self._ethical_repo,
        )

        if self._similarity is not None:
            await enforce_content_policies(
                scenario=scenario,
                current_user=current_user,
                audit=self._audit,
                similarity=self._similarity,
                action="submit_review",
            )

        updated = await self._scenarios_repo.submit_to_queue(
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.SUBMITTED,
            actor_user_id=actor_user_id,
            actor_role=UserRole(current_user.role),
            from_state=scenario.state,
            to_state=updated.state,
        )
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_SUBMITTED_FOR_REVIEW,
            scenario_id=updated.id or "",
            from_state=scenario.state,
            to_state=updated.state,
        )
        await self._notify_reviewers_for_submitted_scenario(
            scenario=updated,
            actor_user_id=actor_user_id,
        )
        return updated

    async def _notify_reviewers_for_submitted_scenario(
        self, *, scenario: ScenarioModel, actor_user_id: str
    ) -> None:
        if self._notifications is None:
            return
        reviewer_ids = await self._assignments_repo.list_reviewer_ids_for_investigator(
            scenario.author_user_id
        )
        for reviewer_id in reviewer_ids:
            if reviewer_id == actor_user_id:
                continue
            await self._notifications.notify_scenario_submitted_for_review(
                reviewer_user_id=reviewer_id,
                scenario=scenario,
                actor_user_id=actor_user_id,
            )

    async def start_applying_changes(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        if not can_start_applying_changes_scenario(user=current_user, scenario=scenario):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot start applying changes on this scenario",
            )
        if not is_valid_transition(scenario.state, ScenarioState.APPLYING_CHANGES):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.start_applying_changes(scenario_id=scenario_id)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.APPLYING_CHANGES_STARTED,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated

    async def start_editing_working_copy(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
    ) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        if not can_start_editing_working_copy(user=current_user, scenario=scenario):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot start editing this scenario",
            )
        if not is_valid_transition(scenario.state, ScenarioState.DRAFT):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")
        updated = await self._scenarios_repo.open_working_copy_from_published(scenario_id=scenario_id)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        actor_user_id = current_user.id or ""
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.DRAFT_SAVED,
            actor_user_id=actor_user_id,
            actor_role=UserRole(current_user.role),
            from_state=scenario.state,
            to_state=updated.state,
        )
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=AuditActionType.SCENARIO_CONTENT_UPDATED,
            scenario_id=updated.id or "",
            from_state=scenario.state,
            to_state=updated.state,
            current_extra={"action": "start_editing_working_copy"},
        )
        return updated

    async def _get_editable_for_assets(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        portfolio = await self._portfolio_for(current_user)
        if not can_update_scenario(
            user=current_user, scenario=scenario, portfolio_investigator_ids=portfolio
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit this scenario")
        return scenario

    @staticmethod
    def _purge_scenario_assets(*, scenario: ScenarioModel, storage: MinioScenarioStorage) -> None:
        storage.ensure_bucket()
        if scenario.cover_image is not None:
            storage.delete_object(storage_key=scenario.cover_image.storage_key)
        for asset in scenario.inline_assets:
            storage.delete_object(storage_key=asset.storage_key)

    async def delete_scenario(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        storage: MinioScenarioStorage,
    ) -> None:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        owner_delete = can_delete_own_scenario(user=current_user, scenario=scenario)
        admin_delete = can_admin_delete_scenario(user=current_user, scenario=scenario)
        if not owner_delete and not admin_delete:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this scenario")

        self._purge_scenario_assets(scenario=scenario, storage=storage)
        if owner_delete and scenario.state == ScenarioState.DRAFT:
            deleted = await self._scenarios_repo.soft_delete_draft(scenario_id=scenario_id)
            action_type = AuditActionType.SCENARIO_DRAFT_DELETED
        else:
            deleted = await self._scenarios_repo.soft_delete_scenario(scenario_id=scenario_id)
            action_type = AuditActionType.SCENARIO_DELETED

        if deleted is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await record_scenario_audit(
            self._audit,
            actor=current_user,
            action_type=action_type,
            scenario_id=scenario_id,
            from_state=scenario.state,
        )

