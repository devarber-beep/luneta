"""Google Gemini API helpers (chat JSON + embeddings)."""
from __future__ import annotations

import asyncio
import logging
import re
import time

from app.settings import settings

logger = logging.getLogger(__name__)

GEMINI_CHAT_MODEL_DEFAULT = "gemini-2.5-flash-lite"
RATE_LIMIT_RETRIES = 2
RATE_LIMIT_BACKOFF_SEC = 2.0


def gemini_chat_model() -> str:
    configured = (settings.gemini_chat_model or "").strip()
    return configured or GEMINI_CHAT_MODEL_DEFAULT


class GeminiApiError(RuntimeError):
    """Gemini API call failed with a user-visible message."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _error_text(exc: Exception) -> str:
    return str(exc)


def _is_rate_limited(exc: Exception) -> bool:
    text = _error_text(exc)
    return "RESOURCE_EXHAUSTED" in text or "429" in text


def _format_gemini_error(exc: Exception, *, model: str | None = None) -> str:
    text = _error_text(exc)
    model_hint = model or gemini_chat_model()
    if _is_rate_limited(exc):
        return (
            "Gemini rate limit reached (shared API quota, not your hourly Luneta limit). "
            "Wait 30–60 seconds and try again. "
            f"Model: {model_hint}."
        )
    if "NOT_FOUND" in text or "404" in text:
        return (
            "Gemini chat model is not available for your API key. "
            f"Check GEMINI_CHAT_MODEL in .env (configured: {model_hint})."
        )
    if "PERMISSION_DENIED" in text or "403" in text:
        return (
            "Gemini API key rejected. Use a key from Google AI Studio (usually starts with AIza). "
            "Check GEMINI_API_KEY in .env."
        )
    match = re.search(r"'message':\s*'([^']+)'", text)
    if match:
        return f"Gemini API error: {match.group(1)}"
    return f"Gemini API error: {text[:280]}"


def gemini_api_key() -> str:
    return (settings.gemini_api_key or "").strip()


def is_gemini_provider() -> bool:
    return (settings.ai_provider or "gemini").strip().lower() == "gemini"


def _client():
    from google import genai

    key = gemini_api_key()
    if not key:
        msg = "Gemini API key is not configured"
        raise RuntimeError(msg)
    return genai.Client(api_key=key)


def _embed_sync(*, texts: list[str]) -> list[list[float]]:
    try:
        client = _client()
        response = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=texts,
        )
        embeddings = response.embeddings
        if not embeddings:
            return []
        return [list(row.values) for row in embeddings]
    except Exception as exc:
        raise GeminiApiError(_format_gemini_error(exc)) from exc


def _generate_with_model(
    *,
    client: object,
    model: str,
    system: str,
    user: str,
    temperature: float,
) -> str:
    from google.genai import types

    response = client.models.generate_content(  # type: ignore[attr-defined]
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            temperature=temperature,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise GeminiApiError("Gemini returned empty content", status_code=None)
    return text


def _generate_json_sync(*, system: str, user: str, temperature: float) -> str:
    client = _client()
    model = gemini_chat_model()
    last_error: Exception | None = None

    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            return _generate_with_model(
                client=client,
                model=model,
                system=system,
                user=user,
                temperature=temperature,
            )
        except GeminiApiError:
            raise
        except Exception as exc:
            last_error = exc
            if _is_rate_limited(exc) and attempt < RATE_LIMIT_RETRIES:
                wait = RATE_LIMIT_BACKOFF_SEC * (attempt + 1)
                logger.warning(
                    "Gemini rate limit on %s (attempt %s), retry in %ss",
                    model,
                    attempt + 1,
                    wait,
                )
                time.sleep(wait)
                continue
            raise GeminiApiError(_format_gemini_error(exc, model=model)) from exc

    if last_error is not None:
        raise GeminiApiError(_format_gemini_error(last_error, model=model)) from last_error
    raise GeminiApiError(f"Gemini request failed for model {model}")


async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return await asyncio.to_thread(_embed_sync, texts=texts)


async def generate_json(*, system: str, user: str, temperature: float = 0.4) -> str:
    return await asyncio.to_thread(
        _generate_json_sync,
        system=system,
        user=user,
        temperature=temperature,
    )
