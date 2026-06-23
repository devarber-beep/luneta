"""Application settings."""
from app.settings import Settings


def test_web_url_fixes_known_site_host_typo() -> None:
    s = Settings(web_url="https://xrforyouthethics.org")
    assert s.web_url == "https://xrforyouthethic.org"


def test_email_from_fixes_known_site_host_typo() -> None:
    s = Settings(email_from="XR <no-reply@xrforyouthethics.org>")
    assert s.email_from == "XR <no-reply@xrforyouthethic.org>"
