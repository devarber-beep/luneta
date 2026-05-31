"""Live OpenAI connectivity check (skipped when OPENAI_API_KEY is unset).

Run manually before release:
  pytest tests/integration/test_openai_connectivity.py -v
"""
from __future__ import annotations

import os

import pytest

from app.settings import settings

pytestmark = pytest.mark.skipif(
    not (settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")).strip(),
    reason="OPENAI_API_KEY not configured",
)


@pytest.mark.asyncio
async def test_openai_embeddings_live() -> None:
    from openai import AsyncOpenAI

    api_key = (settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
    client = AsyncOpenAI(api_key=api_key)
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input="Luneta OpenAI connectivity test",
    )
    vector = response.data[0].embedding
    assert len(vector) >= 100
    assert all(isinstance(x, float) for x in vector[:5])
