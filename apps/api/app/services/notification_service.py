"""In-app notifications and paired transactional email where applicable."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.domain.enums import (
    NotificationEntityType,
    NotificationType,
    UserAccountStatus,
    UserRole,
)
from app.models.notification import NotificationModel
from app.models.scenario import ScenarioModel
from app.models.user import UserModel
from app.repositories.notifications import NotificationsRepository
from app.repositories.users import UsersRepository
from app.services.mailer_service import MailerService, NoopMailer


class NotificationService:
    def __init__(
        self,
        *,
        notifications_repo: NotificationsRepository,
        users_repo: UsersRepository,
        mailer: MailerService | NoopMailer | None = None,
    ) -> None:
        self._notifications = notifications_repo
        self._users = users_repo
        self._mailer = mailer if mailer is not None else MailerService()

    async def notify_suggestion_received(
        self,
        *,
        owner_user_id: str,
        scenario: ScenarioModel,
        suggestion_id: str,
        actor_user_id: str,
    ) -> None:
        scenario_id = scenario.id or ""
        title = scenario.title
        await self._emit(
            recipient_user_id=owner_user_id,
            notification_type=NotificationType.SUGGESTION_RECEIVED,
            title=f"New suggestion on «{title}»",
            message="Someone proposed a change on your scenario.",
            entity_type=NotificationEntityType.SUGGESTION,
            entity_id=suggestion_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path=f"/scenarios/{scenario_id}/edit",
            payload={"suggestion_id": suggestion_id},
            email=lambda email: self._mailer.send_suggestion_created_to_owner(
                to_email=email,
                scenario_title=title,
                scenario_id=scenario_id,
            ),
        )

    async def notify_suggestion_resolved(
        self,
        *,
        suggester_user_id: str,
        scenario: ScenarioModel,
        suggestion_id: str,
        accepted: bool,
        actor_user_id: str,
    ) -> None:
        scenario_id = scenario.id or ""
        title = scenario.title
        outcome = "accepted" if accepted else "rejected"
        ntype = (
            NotificationType.SUGGESTION_ACCEPTED
            if accepted
            else NotificationType.SUGGESTION_REJECTED
        )
        await self._emit(
            recipient_user_id=suggester_user_id,
            notification_type=ntype,
            title=f"Suggestion {outcome} on «{title}»",
            message=f"The scenario owner {outcome} your change suggestion.",
            entity_type=NotificationEntityType.SUGGESTION,
            entity_id=suggestion_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path=f"/scenarios/{scenario_id}/view",
            payload={"suggestion_id": suggestion_id, "outcome": outcome},
            email=lambda email: self._mailer.send_suggestion_resolved_to_author(
                to_email=email,
                scenario_title=title,
                outcome=outcome,
            ),
        )

    async def notify_scenario_submitted_for_review(
        self,
        *,
        reviewer_user_id: str,
        scenario: ScenarioModel,
        actor_user_id: str,
    ) -> None:
        scenario_id = scenario.id or ""
        title = scenario.title
        await self._emit(
            recipient_user_id=reviewer_user_id,
            notification_type=NotificationType.SCENARIO_SUBMITTED_FOR_REVIEW,
            title=f"Scenario submitted for review: «{title}»",
            message="A scenario from an investigator in your portfolio was submitted.",
            entity_type=NotificationEntityType.SCENARIO,
            entity_id=scenario_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path="/review",
            email=lambda email: self._mailer.send_scenario_submitted_for_review(
                to_email=email,
                scenario_title=title,
                scenario_id=scenario_id,
            ),
        )

    async def notify_scenario_published(
        self,
        *,
        owner_user_id: str,
        scenario: ScenarioModel,
        actor_user_id: str,
    ) -> None:
        scenario_id = scenario.id or ""
        title = scenario.public_title or scenario.title
        slug = scenario.public_slug or scenario.slug
        await self._emit(
            recipient_user_id=owner_user_id,
            notification_type=NotificationType.SCENARIO_REVIEW_PUBLISHED,
            title=f"Your scenario is live: «{title}»",
            message="A reviewer published your scenario.",
            entity_type=NotificationEntityType.SCENARIO,
            entity_id=scenario_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path=f"/public/{slug}" if slug else f"/scenarios/{scenario_id}/view",
            email=(
                lambda email: self._mailer.send_scenario_live_to_author(
                    to_email=email,
                    scenario_title=title,
                    public_slug=slug or "",
                )
                if slug
                else None
            ),
        )

    async def notify_scenario_changes_required(
        self,
        *,
        owner_user_id: str,
        scenario: ScenarioModel,
        actor_user_id: str,
        note: str | None,
    ) -> None:
        scenario_id = scenario.id or ""
        title = scenario.title
        await self._emit(
            recipient_user_id=owner_user_id,
            notification_type=NotificationType.SCENARIO_REVIEW_CHANGES_REQUIRED,
            title=f"Changes requested: «{title}»",
            message=note.strip() if note and note.strip() else "A reviewer requested changes before publication.",
            entity_type=NotificationEntityType.SCENARIO,
            entity_id=scenario_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path=f"/scenarios/{scenario_id}/edit",
            payload={"note": note} if note else None,
            email=lambda email: self._mailer.send_review_outcome_to_author(
                to_email=email,
                scenario_title=title,
                outcome="changes_required",
                detail=note,
            ),
        )

    async def notify_scenario_not_suitable(
        self,
        *,
        owner_user_id: str,
        scenario: ScenarioModel,
        actor_user_id: str,
        reason: str | None,
    ) -> None:
        scenario_id = scenario.id or ""
        title = scenario.title
        await self._emit(
            recipient_user_id=owner_user_id,
            notification_type=NotificationType.SCENARIO_REVIEW_NOT_SUITABLE,
            title=f"Scenario marked not suitable: «{title}»",
            message=reason.strip() if reason and reason.strip() else "A reviewer marked this scenario as not suitable.",
            entity_type=NotificationEntityType.SCENARIO,
            entity_id=scenario_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path="/my-scenarios",
            payload={"reason": reason} if reason else None,
            email=lambda email: self._mailer.send_review_outcome_to_author(
                to_email=email,
                scenario_title=title,
                outcome="not_suitable",
                detail=reason,
            ),
        )

    async def notify_scenario_reopened(
        self,
        *,
        owner_user_id: str,
        scenario: ScenarioModel,
        actor_user_id: str,
    ) -> None:
        scenario_id = scenario.id or ""
        title = scenario.title
        await self._emit(
            recipient_user_id=owner_user_id,
            notification_type=NotificationType.SCENARIO_REOPENED,
            title=f"Scenario reopened: «{title}»",
            message="An administrator reopened your scenario so you can edit it again.",
            entity_type=NotificationEntityType.SCENARIO,
            entity_id=scenario_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path=f"/scenarios/{scenario_id}/edit",
            email=lambda email: self._mailer.send_scenario_reopened_to_author(
                to_email=email,
                scenario_title=title,
            ),
        )

    async def notify_collaborator_added(
        self,
        *,
        collaborator_user_id: str,
        scenario: ScenarioModel,
        actor_user_id: str,
    ) -> None:
        if collaborator_user_id == actor_user_id:
            return
        scenario_id = scenario.id or ""
        title = scenario.title
        await self._emit(
            recipient_user_id=collaborator_user_id,
            notification_type=NotificationType.COLLABORATOR_ADDED,
            title=f"You are now a collaborator on «{title}»",
            message="You can view this scenario in your list.",
            entity_type=NotificationEntityType.SCENARIO,
            entity_id=scenario_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path=f"/scenarios/{scenario_id}/view",
        )

    async def notify_investigator_invited(
        self,
        *,
        user: UserModel,
        temporary_password: str,
        verification_token: str,
    ) -> None:
        uid = user.id or ""
        await self._emit(
            recipient_user_id=uid,
            notification_type=NotificationType.INVESTIGATOR_INVITED,
            title="Investigator account created",
            message="Verify your email and change your temporary password on first sign-in.",
            entity_type=NotificationEntityType.USER,
            entity_id=uid,
            link_path="/login",
            email=lambda email: self._mailer.send_investigator_invite(
                to_email=email,
                temporary_password=temporary_password,
                verification_token=verification_token,
            ),
        )

    async def notify_account_status_changed(
        self,
        *,
        user: UserModel,
        previous_status: UserAccountStatus,
        new_status: UserAccountStatus,
        actor_user_id: str,
    ) -> None:
        uid = user.id or ""
        if new_status == UserAccountStatus.DISABLED:
            ntype = NotificationType.ACCOUNT_DISABLED
            title = "Your account was deactivated"
            message = "You can no longer sign in until an administrator reactivates your account."
        else:
            ntype = NotificationType.ACCOUNT_REACTIVATED
            title = "Your account was reactivated"
            message = "You can sign in again."
        await self._emit(
            recipient_user_id=uid,
            notification_type=ntype,
            title=title,
            message=message,
            entity_type=NotificationEntityType.USER,
            entity_id=uid,
            actor_user_id=actor_user_id,
            link_path="/login",
            payload={
                "previous_status": previous_status.value,
                "new_status": new_status.value,
            },
        )

    async def notify_user_role_changed(
        self,
        *,
        user: UserModel,
        previous_role: UserRole,
        new_role: UserRole,
        actor_user_id: str,
    ) -> None:
        uid = user.id or ""
        await self._emit(
            recipient_user_id=uid,
            notification_type=NotificationType.USER_ROLE_CHANGED,
            title=f"Your role changed to {new_role.value}",
            message=f"Your role was updated from {previous_role.value} to {new_role.value}.",
            entity_type=NotificationEntityType.USER,
            entity_id=uid,
            actor_user_id=actor_user_id,
            link_path="/my-profile",
            payload={"previous_role": previous_role.value, "new_role": new_role.value},
        )

    async def notify_scenario_evaluation_received(
        self,
        *,
        scenario: ScenarioModel,
        evaluation_id: str,
        evaluator_user_id: str,
    ) -> None:
        owner_id = scenario.author_user_id
        if evaluator_user_id == owner_id:
            return
        scenario_id = scenario.id or ""
        title = scenario.public_title or scenario.title
        await self._emit(
            recipient_user_id=owner_id,
            notification_type=NotificationType.SCENARIO_EVALUATION_RECEIVED,
            title=f"New ethical evaluation on «{title}»",
            message="A community member submitted an ethical evaluation of your published scenario.",
            entity_type=NotificationEntityType.EVALUATION,
            entity_id=evaluation_id,
            scenario_id=scenario_id,
            actor_user_id=evaluator_user_id,
            link_path=f"/scenarios/{scenario_id}/view",
            payload={"evaluation_id": evaluation_id},
        )

    async def notify_password_changed(self, *, user: UserModel) -> None:
        uid = user.id or ""
        await self._emit(
            recipient_user_id=uid,
            notification_type=NotificationType.PASSWORD_CHANGED,
            title="Password changed",
            message="Your account password was changed. If this was not you, contact support.",
            entity_type=NotificationEntityType.USER,
            entity_id=uid,
            link_path="/my-profile",
            email=lambda email: self._mailer.send_password_changed_notification(to_email=email),
        )

    async def _emit(
        self,
        *,
        recipient_user_id: str,
        notification_type: NotificationType,
        title: str,
        entity_type: NotificationEntityType,
        entity_id: str,
        message: str | None = None,
        scenario_id: str | None = None,
        actor_user_id: str | None = None,
        link_path: str | None = None,
        payload: dict[str, Any] | None = None,
        email: Callable[[str], Awaitable[None]] | None = None,
    ) -> NotificationModel:
        await self._notifications.ensure_indexes()
        row = await self._notifications.create(
            recipient_user_id=recipient_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            scenario_id=scenario_id,
            actor_user_id=actor_user_id,
            link_path=link_path,
            payload=payload,
        )
        if email is not None:
            await self._maybe_send_email(recipient_user_id=recipient_user_id, send=email)
        return row

    async def _maybe_send_email(
        self,
        *,
        recipient_user_id: str,
        send: Callable[[str], Awaitable[None]],
    ) -> None:
        user = await self._users.get_by_id(recipient_user_id)
        if user is None:
            return
        if user.email_verified_at is None:
            return
        if user.account_status != UserAccountStatus.ACTIVE:
            return
        await send(str(user.email_normalized))
