"""Brevo transactional email via HTTPS API (works on hosts that block SMTP)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from email.utils import parseaddr

BREVO_TRANSACTIONAL_URL = "https://api.brevo.com/v3/smtp/email"


def parse_sender(mail_from: str, *, default_sender_name: str = "Luneta") -> tuple[str, str]:
    name, email = parseaddr(mail_from.strip())
    if not email or "@" not in email:
        raise ValueError(f"Invalid EMAIL_FROM address: {mail_from!r}")
    return (name or default_sender_name, email)


def send_brevo_transactional_email_sync(
    *,
    api_key: str,
    mail_from: str,
    to: str,
    subject: str,
    body: str,
    default_sender_name: str = "Luneta",
    timeout_seconds: int = 30,
) -> None:
    sender_name, sender_email = parse_sender(mail_from, default_sender_name=default_sender_name)
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    request = urllib.request.Request(
        BREVO_TRANSACTIONAL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status >= 400:
                detail = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Brevo API HTTP {response.status}: {detail[:500]}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Brevo API HTTP {exc.code}: {detail[:500]}") from exc
