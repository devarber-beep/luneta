"""Brevo HTTPS email client."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.brevo_email import parse_sender, send_brevo_transactional_email_sync


def test_parse_sender_with_display_name() -> None:
    assert parse_sender("Luneta <no-reply@example.org>") == ("Luneta", "no-reply@example.org")


def test_parse_sender_plain_email() -> None:
    assert parse_sender("no-reply@example.org") == ("Luneta", "no-reply@example.org")


def test_parse_sender_invalid() -> None:
    with pytest.raises(ValueError):
        parse_sender("not-an-email")


@patch("app.services.brevo_email.urllib.request.urlopen")
def test_send_brevo_transactional_email_sync_posts_json(mock_urlopen: MagicMock) -> None:
    response = MagicMock()
    response.status = 201
    response.__enter__.return_value = response
    mock_urlopen.return_value = response

    send_brevo_transactional_email_sync(
        api_key="brevo-test-key",
        mail_from="Luneta <sender@example.org>",
        to="user@example.com",
        subject="Hello",
        body="Test body",
    )

    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args.args[0]
    assert request.get_full_url() == "https://api.brevo.com/v3/smtp/email"
    assert request.headers["Api-key"] == "brevo-test-key"
    payload = request.data.decode("utf-8")
    assert "sender@example.org" in payload
    assert "user@example.com" in payload
    assert "Hello" in payload
