"""Scenario service for draft/edit/submit flow."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.core.permissions import (
    can_add_comment,
    can_edit_draft,
    can_manage_collaborators,
    can_submit_for_review,
    can_view_comments,
    get_collaborator_role,
    has_scenario_read_access,
    is_valid_transition,
)
from app.domain.enums import CollaboratorRole, ReviewEventType, ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.scenario_comment import ScenarioCommentModel
from app.models.user import UserModel
from app.repositories.review_events import ReviewEventsRepository
from app.repositories.scenario_comments import ScenarioCommentsRepository
from app.repositories.scenario_revisions import ScenarioRevisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository


class ScenarioService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        revisions_repo: ScenarioRevisionsRepository,
        review_events_repo: ReviewEventsRepository,
        comments_repo: ScenarioCommentsRepository,
        users_repo: UsersRepository,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._revisions_repo = revisions_repo
        self._review_events_repo = review_events_repo
        self._comments_repo = comments_repo
        self._users_repo = users_repo

    async def create_draft(
        self,
        *,
        current_user: UserModel,
        slug: str,
        title: str,
        body_markdown: str,
    ) -> ScenarioModel:
        if current_user.role != UserRole.AUTHOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only authors can create drafts")

        await self._scenarios_repo.ensure_indexes()
        await self._revisions_repo.ensure_indexes()
        await self._review_events_repo.ensure_indexes()

        scenario = await self._scenarios_repo.create(
            slug=slug,
            title=title,
            body_markdown=body_markdown,
            author_user_id=current_user.id or "",
        )
        await self._revisions_repo.create_snapshot(
            scenario_id=scenario.id or "",
            revision_number=scenario.current_revision_number,
            title=scenario.title,
            body_markdown=scenario.body_markdown,
            state_snapshot=scenario.state,
            created_by_user_id=current_user.id or "",
        )
        await self._review_events_repo.create(
            scenario_id=scenario.id or "",
            event_type=ReviewEventType.DRAFT_SAVED,
            actor_user_id=current_user.id or "",
        )
        return scenario

    async def list_my_scenarios(self, *, current_user: UserModel) -> list[ScenarioModel]:
        await self._scenarios_repo.ensure_indexes()
        return await self._scenarios_repo.list_for_participating_user(user_id=current_user.id or "")

    async def get_for_author_or_reviewer(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_role = UserRole(current_user.role)
        actor_user_id = current_user.id or ""
        collaborator_role = get_collaborator_role(scenario=scenario, actor_user_id=actor_user_id)
        if not has_scenario_read_access(actor_role=actor_role, collaborator_role=collaborator_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return scenario

    async def patch_draft(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        title: str | None,
        body_markdown: str | None,
    ) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        collaborator_role = get_collaborator_role(scenario=scenario, actor_user_id=actor_user_id)
        if not can_edit_draft(collaborator_role=collaborator_role, state=scenario.state):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner/editor can edit draft")

        updated = await self._scenarios_repo.update_draft_content(
            scenario_id=scenario_id,
            title=title,
            body_markdown=body_markdown,
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
            body_markdown=bumped.body_markdown,
            state_snapshot=bumped.state,
            created_by_user_id=actor_user_id,
        )
        await self._review_events_repo.create(
            scenario_id=bumped.id or "",
            event_type=ReviewEventType.DRAFT_SAVED,
            actor_user_id=actor_user_id,
        )
        return bumped

    async def submit_review(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        actor_role = UserRole(current_user.role)
        collaborator_role = get_collaborator_role(scenario=scenario, actor_user_id=actor_user_id)
        if not can_submit_for_review(
            actor_role=actor_role,
            collaborator_role=collaborator_role,
            state=scenario.state,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit this scenario")

        if not is_valid_transition(scenario.state, ScenarioState.IN_REVIEW):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid state transition")

        updated = await self._scenarios_repo.set_state(
            scenario_id=scenario_id,
            state=ScenarioState.IN_REVIEW,
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        await self._review_events_repo.create(
            scenario_id=updated.id or "",
            event_type=ReviewEventType.SUBMITTED,
            actor_user_id=actor_user_id,
            from_state=scenario.state,
            to_state=updated.state,
        )
        return updated

    async def list_collaborators(self, *, scenario_id: str, current_user: UserModel):
        scenario = await self.get_for_author_or_reviewer(scenario_id=scenario_id, current_user=current_user)
        return scenario.collaborators, scenario

    async def add_editor(self, *, scenario_id: str, editor_user_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        actor_collaborator_role = get_collaborator_role(scenario=scenario, actor_user_id=actor_user_id)
        if not can_manage_collaborators(collaborator_role=actor_collaborator_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can manage collaborators")

        if editor_user_id == actor_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner is already collaborator")

        editor_user = await self._users_repo.get_by_id(editor_user_id)
        if editor_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Editor user not found")
        if editor_user.role != UserRole.AUTHOR:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only author users can be editors")

        collaborators = [c.model_dump(mode="json") for c in scenario.collaborators]
        for collaborator in collaborators:
            if collaborator["user_id"] == editor_user_id:
                if collaborator["role"] == CollaboratorRole.EDITOR.value:
                    return scenario
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has collaborator role")

        collaborators.append(
            {
                "user_id": editor_user_id,
                "role": CollaboratorRole.EDITOR.value,
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
        )
        return updated

    async def remove_editor(self, *, scenario_id: str, editor_user_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")

        actor_user_id = current_user.id or ""
        actor_collaborator_role = get_collaborator_role(scenario=scenario, actor_user_id=actor_user_id)
        if not can_manage_collaborators(collaborator_role=actor_collaborator_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can manage collaborators")

        filtered = [
            collaborator
            for collaborator in scenario.collaborators
            if not (collaborator.user_id == editor_user_id and collaborator.role == CollaboratorRole.EDITOR)
        ]
        if len(filtered) == len(scenario.collaborators):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Editor collaborator not found")

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
        )
        return updated

    async def list_comments(
        self,
        *,
        scenario_id: str,
        current_user: UserModel | None,
    ) -> list[ScenarioCommentModel]:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        actor_role = UserRole(current_user.role) if current_user is not None else None
        actor_user_id = current_user.id or "" if current_user is not None else ""
        collaborator_role = (
            get_collaborator_role(scenario=scenario, actor_user_id=actor_user_id) if current_user is not None else None
        )
        if not can_view_comments(
            scenario=scenario,
            actor_role=actor_role,
            collaborator_role=collaborator_role,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return await self._comments_repo.list_by_scenario_id(scenario_id=scenario.id or "")

    async def list_public_comments_by_slug(self, *, slug: str) -> tuple[ScenarioModel, list[ScenarioCommentModel]]:
        scenario = await self._scenarios_repo.get_by_slug_and_state(slug=slug, state=ScenarioState.PUBLISHED)
        if scenario is None or scenario.published_at is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        await self._comments_repo.ensure_indexes()
        comments = await self._comments_repo.list_by_scenario_id(scenario_id=scenario.id or "")
        return scenario, comments

    async def add_comment(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        body_markdown: str,
        revision_number: int | None,
        section_key: str | None,
        field_path: str | None,
    ) -> ScenarioCommentModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        actor_role = UserRole(current_user.role)
        collaborator_role = get_collaborator_role(scenario=scenario, actor_user_id=current_user.id or "")
        if not can_add_comment(
            scenario=scenario,
            actor_role=actor_role,
            collaborator_role=collaborator_role,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot comment on this scenario")
        await self._comments_repo.ensure_indexes()
        comment = await self._comments_repo.create(
            scenario_id=scenario.id or "",
            author_user_id=current_user.id or "",
            body_markdown=body_markdown,
            revision_number=revision_number,
            section_key=section_key,
            field_path=field_path,
        )
        await self._review_events_repo.create(
            scenario_id=scenario.id or "",
            event_type=ReviewEventType.COMMENT_ADDED,
            actor_user_id=current_user.id or "",
        )
        return comment

    async def add_public_comment_by_slug(
        self,
        *,
        slug: str,
        current_user: UserModel,
        body_markdown: str,
        revision_number: int | None,
        section_key: str | None,
        field_path: str | None,
    ) -> ScenarioCommentModel:
        scenario = await self._scenarios_repo.get_by_slug_and_state(slug=slug, state=ScenarioState.PUBLISHED)
        if scenario is None or scenario.published_at is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        return await self.add_comment(
            scenario_id=scenario.id or "",
            current_user=current_user,
            body_markdown=body_markdown,
            revision_number=revision_number,
            section_key=section_key,
            field_path=field_path,
        )
