"""Change suggestions on scenarios (review and post-publish collaboration)."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.description_paragraphs import paragraph_count, replace_paragraph, split_paragraphs
from app.core.permissions import get_collaborator_role, is_valid_transition
from app.core.suggestion_access import (
    can_create_suggestion,
    can_list_suggestions,
    can_read_review_feedback_status,
    can_resolve_suggestion,
)
from app.domain.enums import (
    AuditActionType,
    AuditSubjectType,
    CollaboratorRole,
    ReviewEventType,
    ScenarioState,
    SuggestionKind,
    SuggestionScope,
    SuggestionStatus,
    UserRole,
)
from app.models.scenario import ScenarioModel
from app.models.suggestion import SuggestionModel
from app.models.user import UserModel
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.suggestions import SuggestionsRepository
from app.repositories.users import UsersRepository
from app.services.audit_helpers import record_revision_snapshot_audit, record_scenario_audit
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.portfolio_loader import portfolio_investigator_ids_for_user


class SuggestionService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        suggestions_repo: SuggestionsRepository,
        users_repo: UsersRepository,
        assignments_repo: ReviewerAssignmentsRepository,
        review_events_repo: ReviewEventsRepository,
        revisions_repo: ScenarioRevisionsRepository,
        audit_service: AuditService,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._suggestions_repo = suggestions_repo
        self._users_repo = users_repo
        self._assignments_repo = assignments_repo
        self._review_events_repo = review_events_repo
        self._revisions_repo = revisions_repo
        self._audit = audit_service
        self._notifications = notification_service

    async def user_can_create_suggestion(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
    ) -> bool:
        scenario = await self._require_scenario(scenario_id)
        portfolio = await self._portfolio(current_user)
        reviewed = await self._review_events_repo.actor_has_reviewed_scenario(
            scenario_id=scenario_id,
            actor_user_id=current_user.id or "",
        )
        return can_create_suggestion(
            user=current_user,
            scenario=scenario,
            portfolio_investigator_ids=portfolio,
            reviewer_has_reviewed_scenario=reviewed,
        )

    async def pending_post_publication_count(self, *, scenario_id: str) -> int:
        return await self._suggestions_repo.count_pending_post_publication(scenario_id=scenario_id)

    async def pending_post_publication_counts(self, *, scenario_ids: list[str]) -> dict[str, int]:
        return await self._suggestions_repo.count_pending_post_publication_by_scenario_ids(
            scenario_ids=scenario_ids
        )

    async def get_review_feedback_status(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
    ) -> dict[str, bool]:
        scenario = await self._require_scenario(scenario_id)
        portfolio = await self._portfolio(current_user)
        if not can_read_review_feedback_status(
            user=current_user,
            scenario=scenario,
            portfolio_investigator_ids=portfolio,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot read review feedback status")
        has = await self._suggestions_repo.author_has_pending_paragraph_or_scenario_feedback(
            scenario_id=scenario_id,
            author_user_id=current_user.id or "",
        )
        return {"has_submitted_feedback": has}

    async def list_suggestions(self, *, scenario_id: str, current_user: UserModel) -> list[SuggestionModel]:
        scenario = await self._require_scenario(scenario_id)
        uid = current_user.id or ""
        has_authored = await self._suggestions_repo.user_has_authored_suggestions(
            scenario_id=scenario_id,
            author_user_id=uid,
        )
        portfolio = await self._portfolio(current_user)
        reviewed = await self._review_events_repo.actor_has_reviewed_scenario(
            scenario_id=scenario_id,
            actor_user_id=uid,
        )
        if not can_list_suggestions(
            user=current_user,
            scenario=scenario,
            has_authored_suggestion=has_authored,
            portfolio_investigator_ids=portfolio,
            reviewer_has_reviewed_scenario=reviewed,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view suggestions")
        return await self._suggestions_repo.list_for_scenario(scenario_id=scenario_id)

    async def create_suggestion(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        scope: SuggestionScope,
        kind: SuggestionKind,
        paragraph_index: int | None,
        body: str,
    ) -> SuggestionModel:
        scenario = await self._require_scenario(scenario_id)
        portfolio = await self._portfolio(current_user)
        reviewed = await self._review_events_repo.actor_has_reviewed_scenario(
            scenario_id=scenario_id,
            actor_user_id=current_user.id or "",
        )
        if not can_create_suggestion(
            user=current_user,
            scenario=scenario,
            portfolio_investigator_ids=portfolio,
            reviewer_has_reviewed_scenario=reviewed,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create suggestion")
        role = UserRole(current_user.role)
        self._validate_suggestion_shape(
            role=role,
            scope=scope,
            kind=kind,
            paragraph_index=paragraph_index,
            scenario=scenario,
        )
        suggestion = await self._suggestions_repo.create(
            scenario_id=scenario_id,
            author_user_id=current_user.id or "",
            author_role=role,
            scope=scope.value,
            kind=kind.value,
            paragraph_index=paragraph_index,
            body=body,
            scenario_state_at_creation=scenario.state,
        )
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.SUGGESTION_CREATED,
            subject_type=AuditSubjectType.SUGGESTION,
            subject_id=suggestion.id or "",
            current={
                "scenario_id": scenario_id,
                "scope": scope.value,
                "kind": kind.value,
                "paragraph_index": paragraph_index,
            },
        )
        if self._notifications is not None:
            await self._notifications.notify_suggestion_received(
                owner_user_id=scenario.author_user_id,
                scenario=scenario,
                suggestion_id=suggestion.id or "",
                actor_user_id=current_user.id or "",
            )
        return suggestion

    async def accept_suggestion(
        self,
        *,
        scenario_id: str,
        suggestion_id: str,
        current_user: UserModel,
    ) -> tuple[SuggestionModel, ScenarioModel]:
        scenario = await self._require_scenario(scenario_id)
        if not can_resolve_suggestion(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can resolve suggestions")
        suggestion = await self._require_suggestion(suggestion_id)
        if suggestion.scenario_id != scenario_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        if suggestion.status != SuggestionStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suggestion already resolved")
        prior_state = scenario.state
        updated_scenario = await self._apply_accept_side_effects(
            scenario=scenario,
            suggestion=suggestion,
            actor_user=current_user,
        )
        resolved = await self._suggestions_repo.set_status(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.ACCEPTED,
            resolved_by_user_id=current_user.id or "",
        )
        if resolved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.SUGGESTION_ACCEPTED,
            subject_type=AuditSubjectType.SUGGESTION,
            subject_id=suggestion_id,
            previous={"status": SuggestionStatus.PENDING.value},
            current={
                "status": SuggestionStatus.ACCEPTED.value,
                "scenario_id": scenario_id,
                "scope": suggestion.scope,
                "kind": suggestion.kind,
                "paragraph_index": suggestion.paragraph_index,
            },
        )
        if self._notifications is not None:
            await self._notifications.notify_suggestion_resolved(
                suggester_user_id=suggestion.author_user_id,
                scenario=updated_scenario,
                suggestion_id=suggestion_id,
                accepted=True,
                actor_user_id=current_user.id or "",
            )
        await self._record_acceptance_revision(
            scenario=updated_scenario,
            suggestion=resolved,
            actor_user=current_user,
            prior_state=prior_state,
        )
        return resolved, updated_scenario

    async def reject_suggestion(
        self,
        *,
        scenario_id: str,
        suggestion_id: str,
        current_user: UserModel,
    ) -> SuggestionModel:
        scenario = await self._require_scenario(scenario_id)
        if not can_resolve_suggestion(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can resolve suggestions")
        suggestion = await self._require_suggestion(suggestion_id)
        if suggestion.scenario_id != scenario_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        if suggestion.status != SuggestionStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suggestion already resolved")
        resolved = await self._suggestions_repo.set_status(
            suggestion_id=suggestion_id,
            status=SuggestionStatus.REJECTED,
            resolved_by_user_id=current_user.id or "",
        )
        if resolved is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.SUGGESTION_REJECTED,
            subject_type=AuditSubjectType.SUGGESTION,
            subject_id=suggestion_id,
            previous={"status": SuggestionStatus.PENDING.value},
            current={
                "status": SuggestionStatus.REJECTED.value,
                "scenario_id": scenario_id,
                "scope": suggestion.scope,
                "kind": suggestion.kind,
                "paragraph_index": suggestion.paragraph_index,
            },
        )
        if self._notifications is not None:
            await self._notifications.notify_suggestion_resolved(
                suggester_user_id=suggestion.author_user_id,
                scenario=scenario,
                suggestion_id=suggestion_id,
                accepted=False,
                actor_user_id=current_user.id or "",
            )
        return resolved

    async def apply_accepted_suggestion_text(
        self,
        *,
        scenario_id: str,
        suggestion_id: str,
        current_user: UserModel,
    ) -> tuple[SuggestionModel, ScenarioModel]:
        scenario = await self._require_scenario(scenario_id)
        if not can_resolve_suggestion(user=current_user, scenario=scenario):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can apply suggestions")
        if scenario.state not in {ScenarioState.DRAFT, ScenarioState.APPLYING_CHANGES}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Scenario must be in draft or applying changes to apply suggestion text",
            )
        suggestion = await self._require_suggestion(suggestion_id)
        if suggestion.scenario_id != scenario_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        if suggestion.status != SuggestionStatus.ACCEPTED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suggestion must be accepted first")
        if suggestion.kind != SuggestionKind.ALTERNATIVE_TEXT or suggestion.scope != SuggestionScope.PARAGRAPH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only accepted paragraph alternative-text suggestions can be applied",
            )
        if suggestion.applied_at is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Suggestion text already applied")
        if suggestion.paragraph_index is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing paragraph index")
        try:
            new_description = replace_paragraph(
                description=scenario.description,
                paragraph_index=suggestion.paragraph_index,
                new_text=suggestion.body,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        patched = await self._scenarios_repo.update_draft_content(
            scenario_id=scenario_id,
            title=None,
            description=new_description,
        )
        if patched is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        applied = await self._suggestions_repo.mark_applied(suggestion_id=suggestion_id)
        if applied is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        prior_state = patched.state
        bumped = await self._scenarios_repo.bump_revision_number(scenario_id=scenario_id)
        if bumped is not None:
            summary = f"Applied alternative text on paragraph {(suggestion.paragraph_index or 0) + 1}"
            await self._revisions_repo.create_snapshot(
                scenario_id=scenario_id,
                revision_number=bumped.current_revision_number,
                title=bumped.title,
                description=bumped.description,
                state_snapshot=bumped.state,
                created_by_user_id=current_user.id or "",
                accepted_suggestion_id=suggestion.id,
                change_summary=summary,
            )
            await record_revision_snapshot_audit(
                self._audit,
                actor=current_user,
                scenario_id=scenario_id,
                revision_number=bumped.current_revision_number,
                change_summary=summary,
            )
            patched = bumped
        await self._review_events_repo.create(
            scenario_id=scenario_id,
            event_type=ReviewEventType.DRAFT_SAVED,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
            from_state=prior_state,
            to_state=patched.state,
        )
        return applied, patched

    async def _record_acceptance_revision(
        self,
        *,
        scenario: ScenarioModel,
        suggestion: SuggestionModel,
        actor_user: UserModel,
        prior_state: ScenarioState,
    ) -> None:
        scenario_id = scenario.id or ""
        bumped = await self._scenarios_repo.bump_revision_number(scenario_id=scenario_id)
        if bumped is None:
            return
        summary = (
            f"Accepted {suggestion.kind.value} suggestion "
            f"({suggestion.scope.value}"
            + (
                f", paragraph {suggestion.paragraph_index + 1}"
                if suggestion.paragraph_index is not None
                else ""
            )
            + ")"
        )
        await self._revisions_repo.create_snapshot(
            scenario_id=scenario_id,
            revision_number=bumped.current_revision_number,
            title=bumped.title,
            description=bumped.description,
            state_snapshot=bumped.state,
            created_by_user_id=actor_user.id or "",
            accepted_suggestion_id=suggestion.id,
            change_summary=summary,
        )
        await record_revision_snapshot_audit(
            self._audit,
            actor=actor_user,
            scenario_id=scenario_id,
            revision_number=bumped.current_revision_number,
            change_summary=summary,
        )
        await self._review_events_repo.create(
            scenario_id=scenario_id,
            event_type=ReviewEventType.SUGGESTION_ACCEPTED,
            actor_user_id=actor_user.id or "",
            actor_role=UserRole(actor_user.role),
            from_state=prior_state,
            to_state=bumped.state,
        )

    async def _apply_accept_side_effects(
        self,
        *,
        scenario: ScenarioModel,
        suggestion: SuggestionModel,
        actor_user: UserModel,
    ) -> ScenarioModel:
        author_role = UserRole(suggestion.author_role)
        at_creation = suggestion.scenario_state_at_creation
        actor_user_id = actor_user.id or ""
        scenario_id = scenario.id or ""
        actor_role_enum = UserRole(actor_user.role)

        if self._is_reviewer_review_cycle_suggestion(suggestion=suggestion):
            if scenario.state == ScenarioState.CHANGES_REQUIRED and is_valid_transition(
                scenario.state, ScenarioState.APPLYING_CHANGES
            ):
                moved = await self._scenarios_repo.start_applying_changes(scenario_id=scenario_id)
                if moved is not None:
                    await self._review_events_repo.create(
                        scenario_id=scenario_id,
                        event_type=ReviewEventType.APPLYING_CHANGES_STARTED,
                        actor_user_id=actor_user_id,
                        actor_role=actor_role_enum,
                        from_state=scenario.state,
                        to_state=moved.state,
                    )
                    return moved
            return scenario

        if at_creation == ScenarioState.PUBLISHED:
            updated = scenario
            if author_role in {UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.ADMIN}:
                updated = await self._ensure_collaborator(
                    scenario=updated,
                    collaborator_user_id=suggestion.author_user_id,
                    actor_user=actor_user,
                )
            return updated

        return scenario

    @staticmethod
    def _is_reviewer_review_cycle_suggestion(*, suggestion: SuggestionModel) -> bool:
        author_role = UserRole(suggestion.author_role)
        if author_role not in {UserRole.REVIEWER, UserRole.ADMIN}:
            return False
        return suggestion.scenario_state_at_creation in {
            ScenarioState.IN_REVIEW,
            ScenarioState.QUEUED,
        }

    async def _ensure_collaborator(
        self,
        *,
        scenario: ScenarioModel,
        collaborator_user_id: str,
        actor_user: UserModel,
    ) -> ScenarioModel:
        if collaborator_user_id == scenario.author_user_id:
            return scenario
        collaborators = [c.model_dump(mode="json") for c in scenario.collaborators]
        for collab in collaborators:
            if collab["user_id"] == collaborator_user_id:
                return scenario
        actor_user_id = actor_user.id or ""
        now = datetime.now(UTC)
        collaborators.append(
            {
                "user_id": collaborator_user_id,
                "role": CollaboratorRole.COLLABORATOR.value,
                "added_at": now,
                "added_by": actor_user_id,
            }
        )
        updated = await self._scenarios_repo.replace_collaborators(
            scenario_id=scenario.id or "",
            collaborators=collaborators,
        )
        if updated is None:
            return scenario
        await self._review_events_repo.create(
            scenario_id=scenario.id or "",
            event_type=ReviewEventType.COLLABORATOR_ADDED,
            actor_user_id=actor_user_id,
            actor_role=UserRole(actor_user.role),
            from_state=scenario.state,
            to_state=updated.state,
        )
        await record_scenario_audit(
            self._audit,
            actor=actor_user,
            action_type=AuditActionType.SCENARIO_COLLABORATOR_ADDED,
            scenario_id=scenario.id or "",
            current_extra={"collaborator_user_id": collaborator_user_id},
        )
        if self._notifications is not None:
            await self._notifications.notify_collaborator_added(
                collaborator_user_id=collaborator_user_id,
                scenario=updated,
                actor_user_id=actor_user_id,
            )
        return updated

    def _validate_suggestion_shape(
        self,
        *,
        role: UserRole,
        scope: SuggestionScope,
        kind: SuggestionKind,
        paragraph_index: int | None,
        scenario: ScenarioModel,
    ) -> None:
        if scope == SuggestionScope.PARAGRAPH:
            if paragraph_index is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="paragraph_index is required for paragraph suggestions",
                )
            total = paragraph_count(scenario.description)
            if total == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Scenario has no paragraphs to target",
                )
            if paragraph_index < 0 or paragraph_index >= total:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"paragraph_index must be between 0 and {total - 1}",
                )
        elif paragraph_index is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="paragraph_index must be omitted for scenario-level suggestions",
            )
        if scope == SuggestionScope.SCENARIO and kind == SuggestionKind.ALTERNATIVE_TEXT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alternative text applies to paragraphs only",
            )
        if (
            scenario.state == ScenarioState.PUBLISHED
            and scope == SuggestionScope.PARAGRAPH
            and kind == SuggestionKind.COMMENT
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Paragraph suggestions on published scenarios must be alternative text",
            )

    async def _require_scenario(self, scenario_id: str) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return scenario

    async def _require_suggestion(self, suggestion_id: str) -> SuggestionModel:
        suggestion = await self._suggestions_repo.get_by_id(suggestion_id)
        if suggestion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
        return suggestion

    async def _portfolio(self, user: UserModel) -> frozenset[str]:
        return await portfolio_investigator_ids_for_user(
            user=user,
            assignments_repo=self._assignments_repo,
        )
