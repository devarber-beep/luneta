"""Ephemeral AI improvement suggestions for scenario authors."""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any

from fastapi import HTTPException, status

from app.core.description_paragraphs import split_paragraphs
from app.core.permissions import get_collaborator_role
from app.core.scenario_access import can_update_scenario
from app.domain.enums import AuditActionType, AuditSubjectType, CollaboratorRole, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.ai_suggestion_decisions import AiSuggestionDecisionsRepository
from app.repositories.scenarios import ScenariosRepository
from app.schemas.ai_suggestions import (
    AiSuggestionEmptyReason,
    AiSuggestionGenerateResponse,
    AiSuggestionItemResponse,
    AiSuggestionKind,
    AiSuggestionScope,
)
from app.services.audit_service import AuditService
from app.services.gemini_client import (
    GeminiApiError,
    gemini_api_key,
    gemini_chat_model,
    generate_json,
    is_gemini_provider,
)
from app.services.sensitive_data_check import format_finding_labels, scan_scenario_for_sensitive_data
from app.settings import settings

logger = logging.getLogger(__name__)

_MAX_ITEMS = 5
_VALID_SCOPES = frozenset({"title", "description_full", "description_paragraph"})
_VALID_KINDS = frozenset({"clarity", "structure", "safety", "rewrite"})
_CAMEL_TO_SNAKE: dict[str, str] = {
    "paragraphIndex": "paragraph_index",
    "currentExcerpt": "current_excerpt",
    "proposedText": "proposed_text",
}


def _detect_content_language_heuristic(*, title: str, description: str) -> str:
    sample = f"{title}\n{description}".lower()
    spanish_markers = (
        " el ",
        " la ",
        " los ",
        " de ",
        " escenario",
        " niños",
        " niño",
        " aula",
        " estudio",
        " descripción",
    )
    hits = sum(1 for marker in spanish_markers if marker in f" {sample} ")
    return "es" if hits >= 2 else "en"


def _detect_content_language(*, title: str, description: str) -> str:
    sample = f"{title}\n{description}".strip()
    if len(sample) < 25:
        return _detect_content_language_heuristic(title=title, description=description)
    try:
        from langdetect import LangDetectException, detect_langs

        ranked = detect_langs(sample)
        if not ranked:
            return _detect_content_language_heuristic(title=title, description=description)
        top = ranked[0]
        if top.lang in ("es", "ca", "gl") and top.prob >= 0.80:
            return "es"
        if top.lang == "es":
            return "es"
        return "en"
    except LangDetectException:
        return _detect_content_language_heuristic(title=title, description=description)


def _language_instruction(lang: str) -> str:
    if lang == "es":
        return "Write every rationale and proposed_text in Spanish."
    return "Write every rationale and proposed_text in English."


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _field_text_for_scope(
    *,
    scope: str,
    paragraph_index: int | None,
    scenario: ScenarioModel,
) -> str | None:
    if scope == "title":
        return scenario.title or ""
    if scope == "description_full":
        return scenario.description or ""
    if scope == "description_paragraph":
        parts = split_paragraphs(scenario.description)
        if paragraph_index is None or paragraph_index < 0 or paragraph_index >= len(parts):
            return None
        return parts[paragraph_index]
    return None


def _resolve_excerpt_in_text(field_text: str, excerpt: str) -> str | None:
    """Map model excerpt to a verbatim substring of field_text when possible."""
    needle = excerpt.strip()
    if not needle or not field_text:
        return None
    if needle in field_text:
        return needle
    lower_field = field_text.lower()
    lower_needle = needle.lower()
    pos = lower_field.find(lower_needle)
    if pos >= 0:
        return field_text[pos : pos + len(needle)]
    collapsed_field = _collapse_ws(field_text)
    collapsed_needle = _collapse_ws(needle)
    if collapsed_needle and collapsed_needle in collapsed_field:
        if len(collapsed_needle) >= 0.55 * len(collapsed_field):
            return field_text.strip()
    ratio = SequenceMatcher(
        None,
        collapsed_field.lower(),
        collapsed_needle.lower(),
    ).ratio()
    if ratio >= 0.72:
        return field_text.strip()
    return None


def _resolve_excerpt(
    *,
    scope: str,
    paragraph_index: int | None,
    excerpt: str,
    scenario: ScenarioModel,
) -> str | None:
    field_text = _field_text_for_scope(
        scope=scope,
        paragraph_index=paragraph_index,
        scenario=scenario,
    )
    if field_text is None:
        return None
    resolved = _resolve_excerpt_in_text(field_text, excerpt)
    if resolved is not None:
        return resolved
    if scope == "description_paragraph" and paragraph_index is not None:
        parts = split_paragraphs(scenario.description)
        if 0 <= paragraph_index < len(parts):
            return parts[paragraph_index]
    return None


def _strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if not trimmed.startswith("```"):
        return trimmed
    trimmed = re.sub(r"^```(?:json)?\s*", "", trimmed, flags=re.IGNORECASE)
    return re.sub(r"\s*```$", "", trimmed).strip()


def _flatten_llm_items(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [row for row in parsed if isinstance(row, dict)]
    if not isinstance(parsed, dict):
        return []
    candidate = parsed.get("items")
    if isinstance(candidate, list):
        return [row for row in candidate if isinstance(row, dict)]
    if all(key in parsed for key in ("scope", "kind", "proposed_text", "rationale")):
        return [parsed]
    return []


def _normalize_raw_item_keys(raw: dict[str, Any]) -> dict[str, Any]:
    out = dict(raw)
    for camel, snake in _CAMEL_TO_SNAKE.items():
        if camel in out and snake not in out:
            out[snake] = out[camel]
    return out


def _coerce_scope(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _VALID_SCOPES:
        return key
    return None


def _coerce_kind(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    key = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _VALID_KINDS:
        return key
    return None


def _coerce_paragraph_index(
    raw: object,
    *,
    scenario: ScenarioModel,
) -> int | None:
    if raw is None:
        return None
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        return None
    parts = split_paragraphs(scenario.description)
    if not parts:
        return None
    if 0 <= idx < len(parts):
        return idx
    if 1 <= idx <= len(parts):
        return idx - 1
    return None


def _fallback_field_excerpt(
    *,
    scope: str,
    paragraph_index: int | None,
    scenario: ScenarioModel,
) -> str | None:
    field_text = _field_text_for_scope(
        scope=scope,
        paragraph_index=paragraph_index,
        scenario=scenario,
    )
    if field_text and field_text.strip():
        return field_text.strip()
    return None


def _effective_scenario_for_generation(
    scenario: ScenarioModel,
    *,
    draft_title: str | None,
    draft_description: str | None,
) -> ScenarioModel:
    updates: dict[str, str] = {}
    if draft_title is not None:
        updates["title"] = draft_title.strip()
    if draft_description is not None:
        updates["description"] = draft_description.strip()
    if not updates:
        return scenario
    return scenario.model_copy(update=updates)


def _normalize_item(
    raw: dict[str, Any],
    *,
    scenario: ScenarioModel,
) -> AiSuggestionItemResponse | None:
    raw = _normalize_raw_item_keys(raw)
    scope = _coerce_scope(raw.get("scope"))
    kind = _coerce_kind(raw.get("kind"))
    if scope is None or kind is None:
        return None
    excerpt = str(raw.get("current_excerpt") or "").strip()
    proposed = str(raw.get("proposed_text") or "").strip()
    rationale = str(raw.get("rationale") or "").strip()
    if not proposed or not rationale:
        return None
    paragraph_index: int | None = None
    if scope == "description_paragraph":
        paragraph_index = _coerce_paragraph_index(raw.get("paragraph_index"), scenario=scenario)
        if paragraph_index is None:
            return None
    elif raw.get("paragraph_index") is not None:
        return None
    resolved_excerpt = None
    if excerpt:
        resolved_excerpt = _resolve_excerpt(
            scope=scope,
            paragraph_index=paragraph_index,
            excerpt=excerpt,
            scenario=scenario,
        )
    if resolved_excerpt is None:
        resolved_excerpt = _fallback_field_excerpt(
            scope=scope,
            paragraph_index=paragraph_index,
            scenario=scenario,
        )
    if resolved_excerpt is None:
        return None
    return AiSuggestionItemResponse(
        id=str(uuid.uuid4()),
        scope=scope,  # type: ignore[arg-type]
        kind=kind,  # type: ignore[arg-type]
        paragraph_index=paragraph_index,
        current_excerpt=resolved_excerpt,
        proposed_text=proposed,
        rationale=rationale,
    )


class AiSuggestionService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        audit_repo: AuditEventsRepository,
        ai_decisions_repo: AiSuggestionDecisionsRepository,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._audit = AuditService(audit_repo=audit_repo)
        self._ai_decisions_repo = ai_decisions_repo

    async def _require_owner_editable(self, *, scenario_id: str, current_user: UserModel) -> ScenarioModel:
        scenario = await self._scenarios_repo.get_by_id(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
        uid = current_user.id or ""
        if get_collaborator_role(scenario=scenario, user_id=uid) != CollaboratorRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the scenario owner can use AI suggestions",
            )
        if not can_update_scenario(user=current_user, scenario=scenario, portfolio_investigator_ids=frozenset()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Scenario content is not editable in this state",
            )
        return scenario

    async def _enforce_rate_limit(self, *, current_user: UserModel) -> None:
        if UserRole(current_user.role) == UserRole.ADMIN:
            return
        limit = max(1, settings.ai_suggestion_generations_per_hour)
        since = datetime.now(UTC) - timedelta(hours=1)
        count = await self._audit.count_for_actor_since(
            actor_user_id=current_user.id or "",
            action_type=AuditActionType.AI_SUGGESTION_BATCH_GENERATED,
            since=since,
        )
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"You have reached the limit of {limit} AI suggestion generations per hour. "
                    "Try again later."
                ),
            )

    async def generate(
        self,
        *,
        scenario_id: str,
        current_user: UserModel,
        draft_title: str | None = None,
        draft_description: str | None = None,
    ) -> AiSuggestionGenerateResponse:
        scenario = await self._require_owner_editable(scenario_id=scenario_id, current_user=current_user)
        effective = _effective_scenario_for_generation(
            scenario,
            draft_title=draft_title,
            draft_description=draft_description,
        )
        await self._enforce_rate_limit(current_user=current_user)

        if not _llm_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=_llm_not_configured_message(),
            )

        sensitive = scan_scenario_for_sensitive_data(effective)
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.SENSITIVE_DATA_CHECK_RUN,
            subject_type=AuditSubjectType.SCENARIO,
            subject_id=scenario_id,
            current={
                "passed": sensitive.passed,
                "finding_types": sensitive.finding_types,
                "finding_count": len(sensitive.findings),
                "action": "ai_suggestion_generate",
            },
        )
        if not sensitive.passed:
            labels = format_finding_labels(sensitive.finding_types)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "sensitive_data_detected",
                    "message": (
                        "Sensitive or identifiable data detected. AI suggestions cannot be "
                        f"generated until you anonymize or remove: {labels}."
                    ),
                    "finding_types": sensitive.finding_types,
                    "finding_labels": labels,
                    "action": "ai_suggestion_generate",
                },
            )

        items, raw_count, empty_reason, items_filtered_out = await self._call_llm(scenario=effective)
        llm_model = _active_chat_model()
        request_id = str(uuid.uuid4())
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.AI_SUGGESTION_BATCH_GENERATED,
            subject_type=AuditSubjectType.SCENARIO,
            subject_id=scenario_id,
            current={
                "request_id": request_id,
                "item_count": len(items),
                "raw_items_received": raw_count,
                "scopes": list({item.scope for item in items}),
                "provider": llm_model,
                "ai_provider": settings.ai_provider,
                "used_draft_text": draft_title is not None or draft_description is not None,
            },
        )
        return AiSuggestionGenerateResponse(
            request_id=request_id,
            items=items,
            provider=llm_model,
            raw_items_received=raw_count,
            empty_reason=empty_reason,
            items_filtered_out=items_filtered_out,
        )

    async def record_applied(
        self,
        *,
        scenario_id: str,
        item_id: str,
        current_user: UserModel,
        request_id: str,
        scope: AiSuggestionScope,
        kind: AiSuggestionKind,
        paragraph_index: int | None,
        current_excerpt: str,
        proposed_text: str,
        rationale: str,
    ) -> None:
        await self._require_owner_editable(scenario_id=scenario_id, current_user=current_user)
        await self._ai_decisions_repo.create(
            scenario_id=scenario_id,
            request_id=request_id,
            item_id=item_id,
            action="applied",
            scope=scope,
            kind=kind,
            paragraph_index=paragraph_index,
            current_excerpt=current_excerpt,
            proposed_text=proposed_text,
            rationale=rationale,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
        )
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.AI_SUGGESTION_APPLIED,
            subject_type=AuditSubjectType.SCENARIO,
            subject_id=scenario_id,
            current={
                "request_id": request_id,
                "item_id": item_id,
                "scope": scope,
                "kind": kind,
                "paragraph_index": paragraph_index,
            },
        )

    async def record_apply_failed(
        self,
        *,
        scenario_id: str,
        item_id: str,
        current_user: UserModel,
        request_id: str,
        scope: AiSuggestionScope,
        kind: AiSuggestionKind,
        paragraph_index: int | None,
        current_excerpt: str,
        proposed_text: str,
        rationale: str,
        reason: str = "stale_excerpt",
    ) -> None:
        await self._require_owner_editable(scenario_id=scenario_id, current_user=current_user)
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.AI_SUGGESTION_APPLY_FAILED,
            subject_type=AuditSubjectType.SCENARIO,
            subject_id=scenario_id,
            current={
                "request_id": request_id,
                "item_id": item_id,
                "scope": scope,
                "kind": kind,
                "paragraph_index": paragraph_index,
                "reason": reason,
            },
        )

    async def record_discarded(
        self,
        *,
        scenario_id: str,
        item_id: str,
        current_user: UserModel,
        request_id: str,
        scope: AiSuggestionScope,
        kind: AiSuggestionKind,
        paragraph_index: int | None,
        current_excerpt: str,
        proposed_text: str,
        rationale: str,
    ) -> None:
        await self._require_owner_editable(scenario_id=scenario_id, current_user=current_user)
        await self._ai_decisions_repo.create(
            scenario_id=scenario_id,
            request_id=request_id,
            item_id=item_id,
            action="discarded",
            scope=scope,
            kind=kind,
            paragraph_index=paragraph_index,
            current_excerpt=current_excerpt,
            proposed_text=proposed_text,
            rationale=rationale,
            actor_user_id=current_user.id or "",
            actor_role=UserRole(current_user.role),
        )
        await self._audit.record(
            actor=current_user,
            action_type=AuditActionType.AI_SUGGESTION_DISCARDED,
            subject_type=AuditSubjectType.SCENARIO,
            subject_id=scenario_id,
            current={
                "request_id": request_id,
                "item_id": item_id,
                "scope": scope,
                "kind": kind,
                "paragraph_index": paragraph_index,
            },
        )

    async def _call_llm(
        self, *, scenario: ScenarioModel
    ) -> tuple[list[AiSuggestionItemResponse], int, AiSuggestionEmptyReason, int]:
        paragraphs = split_paragraphs(scenario.description)
        lang = _detect_content_language(title=scenario.title, description=scenario.description)
        paragraph_payload = [
            {"index": idx, "text": text} for idx, text in enumerate(paragraphs)
        ]
        system = (
            "You help scenario authors improve educational research scenario drafts. "
            "Return JSON only: one object with key items (array). "
            "Do not wrap JSON in markdown fences. Do not use camelCase or alternate key names. "
            "Suggest concrete text improvements; do not invent facts. "
            "Never include emails, phone numbers, personal names, or addresses in proposed_text. "
            f"{_language_instruction(lang)} "
            f"Return at most {_MAX_ITEMS} suggestions. "
            "Each item must use exactly these snake_case keys and no others: "
            "scope (title|description_full|description_paragraph), "
            "kind (clarity|structure|safety|rewrite), "
            "paragraph_index (integer, required only when scope is description_paragraph), "
            "current_excerpt, proposed_text, rationale. "
            "current_excerpt must be copied verbatim from the draft (exact substring). "
            "If you cannot quote a verbatim excerpt, omit that suggestion."
        )
        user_content = json.dumps(
            {
                "title": scenario.title,
                "description_paragraphs": paragraph_payload,
                "output_schema": {
                    "items": [
                        {
                            "scope": "description_paragraph",
                            "kind": "clarity",
                            "paragraph_index": 0,
                            "current_excerpt": "<verbatim substring from paragraph 0>",
                            "proposed_text": "<replacement for that excerpt>",
                            "rationale": "<short explanation>",
                        }
                    ]
                },
                "rules": {
                    "max_items": _MAX_ITEMS,
                    "scopes": [
                        "title",
                        "description_full",
                        "description_paragraph",
                    ],
                    "kinds": ["clarity", "structure", "safety", "rewrite"],
                    "current_excerpt": (
                        "Copy verbatim from the draft: exact characters from title or "
                        "description (or one paragraph), no paraphrasing."
                    ),
                    "proposed_text": "Replacement text for that excerpt only.",
                    "rationale": "Short explanation why this helps.",
                },
            },
            ensure_ascii=False,
        )
        user_prompt = (
            "Analyze this scenario draft and return "
            '{"items":[...]} using only the snake_case keys from output_schema.\n'
            + user_content
        )
        try:
            if is_gemini_provider():
                raw_text = await generate_json(system=system, user=user_prompt, temperature=0.4)
            else:
                raw_text = await self._call_openai_chat(system=system, user=user_prompt)
        except HTTPException:
            raise
        except GeminiApiError as exc:
            logger.warning("AI suggestion Gemini call failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI suggestion service failed: {exc}",
            ) from exc
        try:
            parsed = json.loads(_strip_json_fence(raw_text))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned invalid JSON",
            ) from exc

        raw_items = _flatten_llm_items(parsed)
        raw_count = len(raw_items)
        items: list[AiSuggestionItemResponse] = []
        for raw in raw_items[: _MAX_ITEMS * 2]:
            item = _normalize_item(raw, scenario=scenario)
            if item is not None:
                items.append(item)
            else:
                logger.warning(
                    "Dropped AI suggestion item (keys=%s)",
                    sorted(raw.keys()),
                )
            if len(items) >= _MAX_ITEMS:
                break
        if raw_count > 0 and not items:
            logger.warning(
                "Gemini returned %s item(s) but none passed normalization",
                raw_count,
            )
        empty_reason: AiSuggestionEmptyReason = "none"
        items_filtered_out = 0
        if not items:
            if raw_count == 0:
                empty_reason = "model_empty"
            else:
                empty_reason = "filtered"
                items_filtered_out = raw_count
        return items, raw_count, empty_reason, items_filtered_out

    async def _call_openai_chat(self, *, system: str, user: str) -> str:
        from openai import AsyncOpenAI

        api_key = (settings.openai_api_key or "").strip()
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=settings.openai_chat_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )
        return (response.choices[0].message.content or "").strip()


def _llm_configured() -> bool:
    if is_gemini_provider():
        return bool(gemini_api_key())
    return bool((settings.openai_api_key or "").strip())


def _llm_not_configured_message() -> str:
    if is_gemini_provider():
        return "AI suggestions are not configured (missing GEMINI_API_KEY)"
    return "AI suggestions are not configured (missing OPENAI_API_KEY)"


def _active_chat_model() -> str:
    if is_gemini_provider():
        return gemini_chat_model()
    return settings.openai_chat_model
