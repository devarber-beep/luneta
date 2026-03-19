"""Mailer service for transactional emails."""


class MailerService:
    async def send_verification_email(self, *, to_email: str, token: str) -> None:
        # Placeholder transport for the slice: keep side effects explicit in logs.
        print(f"[mailer] verify-email to={to_email} token={token}")
