"""Unit tests for Gemini client helpers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.gemini_client import (
    GeminiApiError,
    _format_gemini_error,
    _generate_json_sync,
    _is_rate_limited,
    gemini_chat_model,
)


def test_is_rate_limited_detects_429() -> None:
    assert _is_rate_limited(Exception("429 Too Many Requests"))
    assert _is_rate_limited(Exception("RESOURCE_EXHAUSTED"))


def test_format_rate_limit_message_is_clear() -> None:
    msg = _format_gemini_error(Exception("429 RESOURCE_EXHAUSTED"), model="gemini-2.5-flash-lite")
    assert "rate limit" in msg.lower()
    assert "luneta" in msg.lower() or "30" in msg


def test_generate_json_retries_then_succeeds() -> None:
    client = MagicMock()
    ok_response = MagicMock()
    ok_response.text = '{"items": []}'

    client.models.generate_content.side_effect = [
        Exception("429 RESOURCE_EXHAUSTED"),
        ok_response,
    ]

    with (
        patch("app.services.gemini_client._client", return_value=client),
        patch("app.services.gemini_client.gemini_chat_model", return_value="gemini-2.5-flash-lite"),
        patch("app.services.gemini_client.time.sleep"),
    ):
        raw = _generate_json_sync(system="json", user="{}", temperature=0.0)

    assert "items" in raw
    assert client.models.generate_content.call_count == 2


def test_generate_json_raises_on_persistent_failure() -> None:
    client = MagicMock()
    client.models.generate_content.side_effect = Exception("500 internal")

    with (
        patch("app.services.gemini_client._client", return_value=client),
        patch("app.services.gemini_client.gemini_chat_model", return_value="gemini-2.5-flash-lite"),
    ):
        with pytest.raises(GeminiApiError):
            _generate_json_sync(system="json", user="{}", temperature=0.0)

    assert client.models.generate_content.call_count == 1


def test_default_chat_model_is_flash_lite() -> None:
    with patch("app.services.gemini_client.settings") as mock_settings:
        mock_settings.gemini_chat_model = ""
        assert gemini_chat_model() == "gemini-2.5-flash-lite"
