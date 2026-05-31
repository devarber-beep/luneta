"""Scenario service for draft/edit/submit flow."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.permissions import (
    can_manage_collaborators,
    get_collaborator_role,
    has_republication_pending,
    is_valid_transition,
)
from app.core.scenario_access import (
    can_delete_own_draft,
    can_read_scenario,
    can_start_applying_changes_scenario,
    can_submit_review,
    can_update_scenario,
)
from app.domain.enums import CollaboratorRole, ReviewEventType, ScenarioState, UserAccountStatus, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel
from app.repositories.ethical_risks import EthicalRisksRepository
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenario_classification import ScenarioClassificationRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.services.audit_service import AuditService
from app.services.portfolio_loader import portfolio_investigator_ids_for_user
from app.services.mailer_service import MailerService, NoopMailer
from app.services.content_policy import enforce_content_policies
from app.services.scenario_similarity_service import ScenarioSimilarityService
from app.services.scenario_submit_validation import ensure_ready_for_submit
from app.storage.minio_storage import MinioScenarioStorage


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
        mailer: MailerService | NoopMailer | None = None,
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
        self._mailer = mailer if mailer is not None else MailerService()

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
    ) -> ScenarioModel:
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
        )
        await self._revisions_repo.create_snapshot(
            scenario_id=scenario.id or "",
            revision_number=scenario.current_revision_number,
            title=scenario.title,
            description=scenario.description,
            state_snapshot=scenario.state,
            created_by_user_id=current_user.id or "",
        )
        await self._review_events_repo.create(
            scenario_id=scenario.id or "",
            event_type=ReviewEventType.CREATE_DRAFT,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
            to_state=scenario.state,
        )
        return scenario

    async def list_my_scenarios(self, *, current_user: UserModel) -> list[ScenarioModel]:
        await self._scenarios_repo.ensure_indexes()
        return await self._scenarios_repo.list_for_participating_user(user_id=current_user.id or "")

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
        summary: str | None = None,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
        category_ids: list[str] | None = None,
        ethical_risk_ids: list[str] | None = None,
        sensitive_data_involved: bool | None = None,
    ) -> ScenarioModel:
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

        if self._similarity is not None:
            await enforce_content_policies(
                scenario=scenario,
                current_user=current_user,
                audit=self._audit,
                similarity=self._similarity,
                action="save",
                title=title,
                description=description,
                summary=summary,
            )

        updated = await self._scenarios_repo.update_draft_content(
            scenario_id=scenario_id,
            title=title,
            description=description.strip() if description is not None else None,
            summary=summary,
            categories=categories,
            tags=tags,
            category_ids=category_ids,
            ethical_risk_ids=ethical_risk_ids,
            sensitive_data_involved=sensitive_data_involved,
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
        return bumped

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
        await self._notify_reviewers_for_submitted_scenario(scenario=updated)
        return updated

    async def _notify_reviewers_for_submitted_scenario(self, *, scenario: ScenarioModel) -> None:
        """Email verified reviewers assigned to the scenario owner."""
        addresses: set[str] = set()
        reviewer_ids = await self._assignments_repo.list_reviewer_ids_for_investigator(
            scenario.author_user_id
        )
        for reviewer in (await self._users_repo.get_by_ids(reviewer_ids)).values():
            if (
                reviewer.email_verified_at is not None
                and reviewer.account_status == UserAccountStatus.ACTIVE
            ):
                addresses.add(str(reviewer.email_normalized))
        for address in addresses:
            await self._mailer.send_scenario_submitted_for_review(
                to_email=address,
                scenario_title=scenario.title,
                scenario_id=scenario.id or "",
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

    async def list_collaborators(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self.get_scenario_if_readable(scenario_id=scenario_id, current_user=current_user)
        return scenario.collaborators, scenario

    async def add_collaborator(
        self, *, scenario_id: str, collaborator_user_id: str, current_user: UserModel
    ) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        actor_collaborator_role = get_collaborator_role(scenario=scenario, user_id=actor_user_id)
        if not can_manage_collaborators(collaborator_role=actor_collaborator_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can manage collaborators")

        if collaborator_user_id == actor_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner is already collaborator")

        collaborator_user = await self._users_repo.get_by_id(collaborator_user_id)
        if collaborator_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaborator user not found")
        if collaborator_user.role not in (UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only investigator, reviewer, or admin users can be collaborators",
            )

        collaborators = [c.model_dump(mode="json") for c in scenario.collaborators]
        for collaborator in collaborators:
            if collaborator["user_id"] == collaborator_user_id:
                if collaborator["role"] == CollaboratorRole.COLLABORATOR.value:
                    return scenario
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has collaborator role")

        collaborators.append(
            {
                "user_id": collaborator_user_id,
                "role": CollaboratorRole.COLLABORATOR.value,
                "added_at": datetime.now(UTC),
                "added_by": actor_user_id,
            }
        )
        updated = await self._scenarios_repo.replace_collaborators(
            scenario_id=scenario_id,
            collaborators=collaborators,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.COLLABORATOR_ADDED,
            actor_user_id=actor_user_id,
            actor_role=UserRole(current_user.role),
        )
        return updated

    async def remove_collaborator(
        self, *, scenario_id: str, collaborator_user_id: str, current_user: UserModel
    ) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        actor_collaborator_role = get_collaborator_role(scenario=scenario, user_id=actor_user_id)
        if not can_manage_collaborators(collaborator_role=actor_collaborator_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can manage collaborators")

        filtered = [
            collaborator
            for collaborator in scenario.collaborators
            if not (
                collaborator.user_id == collaborator_user_id
                and collaborator.role == CollaboratorRole.COLLABORATOR
            )
        ]
        if len(filtered) == len(scenario.collaborators):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collaborator not found")

        updated = await self._scenarios_repo.replace_collaborators(
            scenario_id=scenario_id,
            collaborators=[c.model_dump(mode="json") for c in filtered],
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.COLLABORATOR_REMOVED,
            actor_user_id=actor_user_id,
            actor_role=UserRole(current_user.role),
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

    async def delete_draft(self, *, scenario_id: str, current_user: UserModel) -> None:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        if not can_delete_own_draft(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this scenario")
        deleted = await self._scenarios_repo.soft_delete_draft(scenario_id=scenario_id)
        if deleted is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

