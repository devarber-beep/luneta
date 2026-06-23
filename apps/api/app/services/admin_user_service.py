"""Admin-only user lifecycle actions (accounts, roles, status)."""

from __future__ import annotations



import secrets



from fastapi import HTTPException, status



from app.core.security import hash_password
from app.core.user_display_name import parse_person_names

from app.domain.enums import AuditActionType, AuditSubjectType, UserAccountStatus, UserRole

from app.models.user import UserModel

from app.repositories.email_verification_tokens import EmailVerificationTokensRepository

from app.repositories.users import UsersRepository

from app.services.audit_service import AuditService

from app.services.email_verification_service import EmailVerificationService

from app.services.mailer_service import MailerService

from app.services.notification_service import NotificationService





class AdminUserService:

    def __init__(

        self,

        *,

        users_repo: UsersRepository,

        tokens_repo: EmailVerificationTokensRepository,

        notification_service: NotificationService,

        email_verification_token_ttl_minutes: int,

        audit_service: AuditService | None = None,

    ) -> None:

        self._users_repo = users_repo

        self._tokens_repo = tokens_repo

        self._notifications = notification_service

        self._email_verification_token_ttl_minutes = email_verification_token_ttl_minutes

        self._audit = audit_service



    async def create_investigator_account(

        self,

        *,

        actor: UserModel,

        email: str,

        first_name: str,

        last_name: str,

    ) -> UserModel:

        if await self._users_repo.get_by_email(email) is not None:

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        try:

            fn, ln, _, _ = parse_person_names(first_name=first_name, last_name=last_name)

        except ValueError as exc:

            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc



        temporary_password = secrets.token_urlsafe(14)

        user = await self._users_repo.create(

            email=email.strip(),

            password_hash=hash_password(temporary_password),

            role=UserRole.INVESTIGATOR,

            first_name=fn,

            last_name=ln,

            must_change_password=True,

        )

        uid = user.id or ""

        ev = EmailVerificationService(

            tokens_repo=self._tokens_repo,

            users_repo=self._users_repo,

            token_ttl_minutes=self._email_verification_token_ttl_minutes,

        )

        verification_token = await ev.issue_token(user_id=uid, email=str(user.email_normalized))

        await self._notifications.notify_investigator_invited(

            user=user,

            temporary_password=temporary_password,

            verification_token=verification_token,

        )

        if self._audit is not None:

            await self._audit.record(

                actor=actor,

                action_type=AuditActionType.INVESTIGATOR_ACCOUNT_CREATED,

                subject_type=AuditSubjectType.USER,

                subject_id=uid,

                current={

                    "email_normalized": str(user.email_normalized),

                    "role": user.role.value,

                    "account_status": user.account_status.value,

                    "must_change_password": user.must_change_password,

                },

            )

        return user



    async def set_user_role(self, *, actor: UserModel, target_user_id: str, new_role: UserRole) -> UserModel:

        user = await self._users_repo.get_by_id(target_user_id)

        if user is None:

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        current = UserRole(user.role)

        if new_role == current:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has this role")

        if current == UserRole.ADMIN and new_role != UserRole.ADMIN:
            admin_count = await self._users_repo.count_by_role(UserRole.ADMIN)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot change role of the last admin account",
                )

        updated = await self._users_repo.set_role(target_user_id, role=new_role)

        if updated is None:

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if self._audit is not None:

            await self._audit.record(

                actor=actor,

                action_type=AuditActionType.USER_ROLE_CHANGED,

                subject_type=AuditSubjectType.USER,

                subject_id=target_user_id,

                previous={"role": current.value},

                current={"role": new_role.value},

            )

        await self._notifications.notify_user_role_changed(

            user=updated,

            previous_role=current,

            new_role=new_role,

            actor_user_id=actor.id or "",

        )

        return updated



    async def set_account_status(

        self, *, actor: UserModel, target_user_id: str, account_status: UserAccountStatus

    ) -> UserModel:

        user = await self._users_repo.get_by_id(target_user_id)

        if user is None:

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.account_status == account_status:

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already has this status")

        previous_status = user.account_status

        updated = await self._users_repo.set_account_status(target_user_id, account_status=account_status)

        if updated is None:

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if self._audit is not None:

            await self._audit.record(

                actor=actor,

                action_type=AuditActionType.USER_ACCOUNT_STATUS_CHANGED,

                subject_type=AuditSubjectType.USER,

                subject_id=target_user_id,

                previous={"account_status": previous_status.value},

                current={"account_status": account_status.value},

            )

        await self._notifications.notify_account_status_changed(

            user=updated,

            previous_status=previous_status,

            new_status=account_status,

            actor_user_id=actor.id or "",

        )

        return updated



    async def verify_user_email(self, *, actor: UserModel, target_user_id: str) -> UserModel:

        user = await self._users_repo.get_by_id(target_user_id)

        if user is None:

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.email_verified_at is not None:

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already verified")

        if not await self._users_repo.mark_email_verified(target_user_id):

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already verified")

        updated = await self._users_repo.get_by_id(target_user_id)

        if updated is None:

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if self._audit is not None:

            await self._audit.record(

                actor=actor,

                action_type=AuditActionType.USER_EMAIL_VERIFIED_BY_ADMIN,

                subject_type=AuditSubjectType.USER,

                subject_id=target_user_id,

                previous={"email_verified": False},

                current={"email_verified": True},

            )

        await MailerService().send_email_verified_confirmation(to_email=str(updated.email_normalized))

        return updated

