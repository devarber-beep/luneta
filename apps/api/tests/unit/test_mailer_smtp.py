"""SMTP transport helpers for transactional mail."""
from unittest.mock import MagicMock, patch

from app.services.mailer_service import _send_smtp_sync, _smtp_transport_mode


def test_smtp_transport_mode_ports() -> None:
    assert _smtp_transport_mode(1025) == (False, False)
    assert _smtp_transport_mode(587) == (True, False)
    assert _smtp_transport_mode(465) == (False, True)


@patch("app.services.mailer_service.smtplib.SMTP")
def test_send_smtp_sync_uses_starttls_and_login_on_587(mock_smtp_class: MagicMock) -> None:
    smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = smtp

    _send_smtp_sync(
        host="smtp-relay.brevo.com",
        port=587,
        mail_from="Luneta <no-reply@luneta.org>",
        to="user@example.com",
        subject="Test",
        body="Hello",
        username="sender@example.com",
        password="smtp-key",
    )

    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("sender@example.com", "smtp-key")
    smtp.send_message.assert_called_once()


@patch("app.services.mailer_service.smtplib.SMTP")
def test_send_smtp_sync_skips_tls_and_login_for_mailhog(mock_smtp_class: MagicMock) -> None:
    smtp = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = smtp

    _send_smtp_sync(
        host="localhost",
        port=1025,
        mail_from="Luneta <no-reply@luneta.local>",
        to="user@example.com",
        subject="Test",
        body="Hello",
    )

    smtp.starttls.assert_not_called()
    smtp.login.assert_not_called()
    smtp.send_message.assert_called_once()
