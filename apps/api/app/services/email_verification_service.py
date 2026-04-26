"""Service to create and consume email verification tokens."""
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from app.core.security import hash_email_token
from app.repositories.email_verification_tokens import EmailVerificationTokensRepository
from app.repositories.users import UsersRepository


class EmailVerificationService:
    def __init__(
        self,
        *,
        tokens_repo: EmailVerificationTokensRepository,
        users_repo: UsersRepository,
        token_ttl_minutes: int,
    ) -> None:
        self._tokens_repo = tokens_repo
        self._users_repo = users_repo
        self._token_ttl_minutes = token_ttl_minutes

    async def issue_token(self, *, user_id: str, email: str) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_email_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(minutes=self._token_ttl_minutes)
        await self._tokens_repo.create(
            user_id=user_id,
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        return raw_token

    async def verify(self, *, token: str) -> str | None:
        """Return the user's email if verification succeeded, else None."""
        token_hash = hash_email_token(token)
        token_record = await self._tokens_repo.get_active_by_token_hash(token_hash)
        if token_record is None:
            return None
        consumed = await self._tokens_repo.consume(token_record.id or "")
        if not consumed:
            return None
        if not await self._users_repo.mark_email_verified(token_record.user_id):
            return None
        return token_record.email
