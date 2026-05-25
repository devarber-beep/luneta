"""Transactional email delivery (SMTP)."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.settings import settings

logger = logging.getLogger(__name__)


def _send_smtp_sync(*, host: str, port: int, mail_from: str, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.send_message(msg)


class NoopMailer:
    """Test double: no network I/O."""

    async def send_verification_email(self, *, to_email: str, token: str) -> None:
        return None

    async def send_email_verified_confirmation(self, *, to_email: str) -> None:
        return None

    async def send_password_changed_notification(self, *, to_email: str) -> None:
        return None

    async def send_scenario_submitted_for_review(
        self,
        *,
        to_email: str,
        scenario_title: str,
        scenario_id: str,
    ) -> None:
        return None

    async def send_scenario_live_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
        public_slug: str,
    ) -> None:
        return None

    async def send_review_outcome_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
        outcome: str,
        detail: str | None,
    ) -> None:
        return None

    async def send_scenario_reopened_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
    ) -> None:
        return None

    async def send_investigator_invite(
        self,
        *,
        to_email: str,
        temporary_password: str,
        verification_token: str,
    ) -> None:
        return None

    async def send_suggestion_created_to_owner(
        self,
        *,
        to_email: str,
        scenario_title: str,
        scenario_id: str,
    ) -> None:
        return None

    async def send_suggestion_resolved_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
        outcome: str,
    ) -> None:
        return None


class MailerService:
    def __init__(self) -> None:
        self._s = settings

    async def _send(self, *, to_email: str, subject: str, body: str) -> None:
        try:

            def _run() -> None:
                _send_smtp_sync(
                    host=self._s.email_smtp_host,
                    port=self._s.email_smtp_port,
                    mail_from=self._s.email_from,
                    to=to_email,
                    subject=subject,
                    body=body,
                )

            await asyncio.to_thread(_run)
            logger.info("email sent to=%s subject=%s", to_email, subject)
        except Exception:
            logger.exception("email failed to=%s subject=%s", to_email, subject)
            if not self._s.email_fail_silently:
                raise

    async def send_verification_email(self, *, to_email: str, token: str) -> None:
        base = self._s.web_url.rstrip("/")
        link = f"{base}/verify-email?token={token}"
        subject = "Verify your Luneta email"
        body = (
            f"Welcome to Luneta.\n\n"
            f"Open this link to verify your email (or paste the token on the verify page):\n{link}\n\n"
            f"If you did not sign up, you can ignore this message.\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_email_verified_confirmation(self, *, to_email: str) -> None:
        subject = "Your Luneta email is verified"
        body = "Your email address has been verified. You can sign in to Luneta.\n"
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_password_changed_notification(self, *, to_email: str) -> None:
        subject = "Your Luneta password was changed"
        body = (
            "The password for your Luneta account was just changed.\n\n"
            "If this was not you, contact support immediately and secure your email inbox.\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_scenario_submitted_for_review(
        self,
        *,
        to_email: str,
        scenario_title: str,
        scenario_id: str,
    ) -> None:
        base = self._s.web_url.rstrip("/")
        review_url = f"{base}/review"
        subject = f"Scenario submitted for review: {scenario_title}"
        body = (
            f"A scenario was submitted for review.\n\n"
            f"Title: {scenario_title}\n"
            f"Scenario id: {scenario_id}\n\n"
            f"Open the review queue: {review_url}\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_scenario_live_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
        public_slug: str,
    ) -> None:
        base = self._s.web_url.rstrip("/")
        public_url = f"{base}/public/{public_slug}"
        subject = f"Your scenario is live: {scenario_title}"
        body = (
            f"Your scenario has been published.\n\n"
            f"Title: {scenario_title}\n"
            f"Public link: {public_url}\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_review_outcome_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
        outcome: str,
        detail: str | None,
    ) -> None:
        base = self._s.web_url.rstrip("/")
        mine_url = f"{base}/mine"
        if outcome == "changes_required":
            subject = f"Changes requested for your scenario: {scenario_title}"
            lead = "A reviewer requested changes before this scenario can be published."
        else:
            subject = f"Scenario marked as not suitable: {scenario_title}"
            lead = "A reviewer marked this scenario as not suitable for publication."
        body = f"{lead}\n\nTitle: {scenario_title}\n"
        if detail:
            body += f"\nReviewer note:\n{detail}\n"
        body += f"\nOpen your scenarios: {mine_url}\n"
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_scenario_reopened_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
    ) -> None:
        subject = f"Your scenario was reopened: {scenario_title}"
        base = self._s.web_url.rstrip("/")
        body = (
            f"An administrator reopened your scenario so you can edit it again.\n\n"
            f"Title: {scenario_title}\n\n"
            f"Open your scenarios: {base}/mine\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_investigator_invite(
        self,
        *,
        to_email: str,
        temporary_password: str,
        verification_token: str,
    ) -> None:
        base = self._s.web_url.rstrip("/")
        link = f"{base}/verify-email?token={verification_token}"
        subject = "Your Luneta investigator account"
        body = (
            "An administrator has created an investigator account for this email address in Luneta.\n\n"
            f"Your temporary password (you must change it after first successful sign-in): {temporary_password}\n\n"
            f"Verify your email before signing in:\n{link}\n\n"
            "If you did not expect this message, contact your administrator.\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_suggestion_created_to_owner(
        self,
        *,
        to_email: str,
        scenario_title: str,
        scenario_id: str,
    ) -> None:
        base = self._s.web_url.rstrip("/")
        edit_url = f"{base}/scenarios/{scenario_id}/edit"
        subject = f"New change suggestion: {scenario_title}"
        body = (
            f"Someone submitted a change suggestion on your scenario.\n\n"
            f"Title: {scenario_title}\n"
            f"Review suggestions: {edit_url}\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)

    async def send_suggestion_resolved_to_author(
        self,
        *,
        to_email: str,
        scenario_title: str,
        outcome: str,
    ) -> None:
        subject = f"Your suggestion was {outcome}: {scenario_title}"
        body = (
            f"The scenario owner {outcome} your change suggestion.\n\n"
            f"Scenario: {scenario_title}\n"
        )
        await self._send(to_email=to_email, subject=subject, body=body)
