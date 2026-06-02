"""Google Gemini API helpers (chat JSON + embeddings)."""
from __future__ import annotations

import asyncio
import re

from app.settings import settings

# Suggestions chat: fixed model (free tier friendly).
GEMINI_CHAT_MODEL_ID = "gemini-2.5-flash-lite"


def gemini_chat_model() -> str:
    return GEMINI_CHAT_MODEL_ID


class GeminiApiError(RuntimeError):
    """Gemini API call failed with a user-visible message."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _format_gemini_error(exc: Exception) -> str:
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        return (
            "Gemini quota exceeded for this model. Wait a minute and try again, "
            f"or wait and retry (chat model: {GEMINI_CHAT_MODEL_ID})."
        )
    if "NOT_FOUND" in text or "404" in text:
        return (
            "Gemini model not found or not enabled for your API key. "
            f"Check GEMINI_EMBEDDING_MODEL in .env (chat uses {GEMINI_CHAT_MODEL_ID})."
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


def _generate_json_sync(*, system: str, user: str, temperature: float) -> str:
    from google.genai import types

    try:
        client = _client()
        response = client.models.generate_content(
            model=gemini_chat_model(),
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=temperature,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise GeminiApiError("Gemini returned empty content")
        return text
    except GeminiApiError:
        raise
    except Exception as exc:
        raise GeminiApiError(_format_gemini_error(exc)) from exc


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
