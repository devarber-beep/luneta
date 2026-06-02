"""Optional live check against Gemini (skipped without GEMINI_API_KEY).

Run:
  pytest tests/integration/test_gemini_connectivity.py -v
"""
from __future__ import annotations

import os

import pytest

from app.settings import settings


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")).strip(),
    reason="GEMINI_API_KEY not set",
)
async def test_gemini_embeddings_live() -> None:
    from app.services.gemini_client import embed_texts

    vectors = await embed_texts(["hello world", "classroom observation study"])
    assert len(vectors) == 2
    assert len(vectors[0]) > 10


@pytest.mark.asyncio
@pytest.mark.skipif(
    not (settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")).strip(),
    reason="GEMINI_API_KEY not set",
)
async def test_gemini_json_chat_live() -> None:
    from app.services.gemini_client import generate_json

    raw = await generate_json(
        system='Return JSON only: {"ok": true}',
        user='Reply with {"ok": true}',
        temperature=0.0,
    )
    assert "ok" in raw
