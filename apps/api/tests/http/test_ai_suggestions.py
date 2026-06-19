"""HTTP tests for ephemeral AI improvement suggestions."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from tests.http.test_ai_assistance import _signup_investigator


def _openai_items_payload() -> str:
    return json.dumps(
        {
            "items": [
                {
                    "scope": "title",
                    "kind": "clarity",
                    "current_excerpt": "Contact study",
                    "proposed_text": "Classroom observation study",
                    "rationale": "Clearer purpose for readers.",
                },
                {
                    "scope": "description_paragraph",
                    "kind": "structure",
                    "paragraph_index": 0,
                    "current_excerpt": "A classroom observation study.",
                    "proposed_text": "An observational study in primary classrooms.",
                    "rationale": "Adds setting detail.",
                },
            ]
        }
    )


def _mock_openai_chat(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


def _patch_gemini(monkeypatch) -> None:
    monkeypatch.setattr("app.settings.settings.ai_provider", "gemini")
    monkeypatch.setattr("app.settings.settings.gemini_api_key", "test-gemini-key")


@pytest.mark.asyncio
async def test_generate_ai_suggestions_for_owner(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug@luneta.dev", token="ai-sug-1"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]

    with patch(
        "app.services.ai_suggestion_service.generate_json",
        new=AsyncMock(return_value=_openai_items_payload()),
    ):
        gen = await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)

    assert gen.status_code == 200
    body = gen.json()
    assert body["request_id"]
    assert len(body["items"]) == 2
    assert body["items"][0]["rationale"]

    audit = await fake_db["audit_events"].find_one({"action_type": "ai_suggestion_batch_generated"})
    assert audit is not None
    assert audit["current"]["item_count"] == 2


@pytest.mark.asyncio
async def test_generate_blocked_when_sensitive(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug2@luneta.dev", token="ai-sug-2"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]

    gen = await api_client.post(
        f"/scenarios/{sid}/ai-suggestions/generate",
        headers=headers,
        json={"description": "Email teacher@school.edu for coordination."},
    )
    assert gen.status_code == 400
    detail = gen.json()["detail"]
    assert detail["code"] == "sensitive_data_detected"


@pytest.mark.asyncio
async def test_rate_limit_non_admin(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    monkeypatch.setattr("app.settings.settings.ai_suggestion_generations_per_hour", 2)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug3@luneta.dev", token="ai-sug-3"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Pilot study", "description": "Observation in schools."},
        headers=headers,
    )
    sid = create.json()["id"]

    with patch(
        "app.services.ai_suggestion_service.generate_json",
        new=AsyncMock(return_value=_openai_items_payload()),
    ):
        assert (
            await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)
        ).status_code == 200
        assert (
            await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)
        ).status_code == 200
        third = await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)

    assert third.status_code == 429


def _gemini_legacy_keys_payload() -> str:
    return json.dumps(
        {
            "items": [
                {
                    "scope": "description",
                    "kind": "clear",
                    "suggestion": "An observational study in primary classrooms.",
                    "reason": "Adds setting detail.",
                },
                {
                    "scope": "paragraph",
                    "paragraph_index": 1,
                    "replacement": "Sharper opening sentence.",
                    "explanation": "Stronger hook.",
                },
            ]
        }
    )


@pytest.mark.asyncio
async def test_generate_rejects_legacy_field_names(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug-alias@luneta.dev", token="ai-sug-alias"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]

    with patch(
        "app.services.ai_suggestion_service.generate_json",
        new=AsyncMock(return_value=_gemini_legacy_keys_payload()),
    ):
        gen = await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)

    assert gen.status_code == 200
    body = gen.json()
    assert body["raw_items_received"] == 2
    assert body["items"] == []
    assert body["empty_reason"] == "filtered"
    assert body["items_filtered_out"] == 2


def _gemini_camel_case_payload() -> str:
    return json.dumps(
        {
            "items": [
                {
                    "scope": "title",
                    "kind": "clarity",
                    "currentExcerpt": "Contact study",
                    "proposedText": "Classroom observation study",
                    "rationale": "Clearer purpose.",
                },
                {
                    "scope": "description_paragraph",
                    "kind": "structure",
                    "paragraphIndex": 0,
                    "currentExcerpt": "A classroom observation study.",
                    "proposedText": "An observational study in primary classrooms.",
                    "rationale": "Adds setting detail.",
                },
            ]
        }
    )


@pytest.mark.asyncio
async def test_generate_accepts_gemini_camel_case_keys(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug-camel@luneta.dev", token="ai-sug-camel"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]

    with patch(
        "app.services.ai_suggestion_service.generate_json",
        new=AsyncMock(return_value=_gemini_camel_case_payload()),
    ):
        gen = await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)

    assert gen.status_code == 200
    body = gen.json()
    assert body["raw_items_received"] == 2
    assert len(body["items"]) == 2
    assert body["empty_reason"] == "none"


@pytest.mark.asyncio
async def test_generate_empty_model_returns_model_empty(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug-empty@luneta.dev", token="ai-sug-empty"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]

    with patch(
        "app.services.ai_suggestion_service.generate_json",
        new=AsyncMock(return_value='{"items": []}'),
    ):
        gen = await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)

    assert gen.status_code == 200
    body = gen.json()
    assert body["items"] == []
    assert body["empty_reason"] == "model_empty"
    assert body["raw_items_received"] == 0


@pytest.mark.asyncio
async def test_generate_filtered_returns_filtered_reason(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug-filt@luneta.dev", token="ai-sug-filt"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]

    with patch(
        "app.services.ai_suggestion_service.generate_json",
        new=AsyncMock(return_value='{"items": [{"scope": "invalid", "kind": "nope"}]}'),
    ):
        gen = await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)

    assert gen.status_code == 200
    body = gen.json()
    assert body["items"] == []
    assert body["empty_reason"] == "filtered"
    assert body["items_filtered_out"] == 1


@pytest.mark.asyncio
async def test_record_apply_failed_writes_audit(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug-fail@luneta.dev", token="ai-sug-fail"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]
    payload = {
        "request_id": "req-fail-1",
        "scope": "title",
        "kind": "clarity",
        "current_excerpt": "Old title",
        "proposed_text": "New title",
        "rationale": "Clearer.",
    }
    failed = await api_client.post(
        f"/scenarios/{sid}/ai-suggestions/item-1/apply-failed",
        headers=headers,
        json=payload,
    )
    assert failed.status_code == 200
    audit = await fake_db["audit_events"].find_one({"action_type": "ai_suggestion_apply_failed"})
    assert audit is not None
    assert audit["current"]["reason"] == "stale_excerpt"


@pytest.mark.asyncio
async def test_record_applied_and_discarded(api_client, fake_db, monkeypatch) -> None:
    _patch_gemini(monkeypatch)
    headers = await _signup_investigator(
        api_client, fake_db, email="ai-sug4@luneta.dev", token="ai-sug-4"
    )
    create = await api_client.post(
        "/scenarios",
        json={"title": "Contact study", "description": "A classroom observation study."},
        headers=headers,
    )
    sid = create.json()["id"]

    with patch(
        "app.services.ai_suggestion_service.generate_json",
        new=AsyncMock(return_value=_openai_items_payload()),
    ):
        gen = await api_client.post(f"/scenarios/{sid}/ai-suggestions/generate", headers=headers)
    item = gen.json()["items"][0]
    payload = {
        "request_id": gen.json()["request_id"],
        "scope": item["scope"],
        "kind": item["kind"],
        "paragraph_index": item.get("paragraph_index"),
        "current_excerpt": item["current_excerpt"],
        "proposed_text": item["proposed_text"],
        "rationale": item["rationale"],
    }
    applied = await api_client.post(
        f"/scenarios/{sid}/ai-suggestions/{item['id']}/applied",
        headers=headers,
        json=payload,
    )
    assert applied.status_code == 200

    discarded = await api_client.post(
        f"/scenarios/{sid}/ai-suggestions/other-id/discard",
        headers=headers,
        json=payload,
    )
    assert discarded.status_code == 200

    assert await fake_db["audit_events"].find_one({"action_type": "ai_suggestion_applied"})
    assert await fake_db["audit_events"].find_one({"action_type": "ai_suggestion_discarded"})
    applied_doc = await fake_db["ai_suggestion_decisions"].find_one({"action": "applied"})
    discarded_doc = await fake_db["ai_suggestion_decisions"].find_one({"action": "discarded"})
    assert applied_doc is not None
    assert discarded_doc is not None
    assert applied_doc["proposed_text"] == item["proposed_text"]
