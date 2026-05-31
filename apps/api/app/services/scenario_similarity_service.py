"""Similarity check between a draft scenario and existing published scenarios."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.scenario import ScenarioModel
from app.models.user import UserModel
from app.repositories.scenarios import ScenariosRepository
from app.services.audit_service import AuditService
from app.domain.enums import AuditActionType, AuditSubjectType
from app.settings import settings

_HEURISTIC_MIN_SCORE = 0.28
_EMBEDDING_MIN_SCORE = 0.82


@dataclass(frozen=True)
class SimilarityCandidate:
    scenario_id: str
    title: str
    score: float
    public_path: str | None = None


def _public_path_for(scenario: ScenarioModel) -> str | None:
    slug = scenario.public_slug
    if isinstance(slug, str) and slug.strip():
        return f"/public/{slug.strip()}"
    return None


@dataclass(frozen=True)
class SimilarityCheckResult:
    candidates: list[SimilarityCandidate]
    provider: str


def _token_set(text: str) -> set[str]:
    return {tok for tok in re.split(r"\W+", text.lower()) if len(tok) >= 3}


def _heuristic_score(left: str, right: str) -> float:
    a = _token_set(left)
    b = _token_set(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(x * y for x, y in zip(left, right, strict=True))
    norm_left = sum(x * x for x in left) ** 0.5
    norm_right = sum(y * y for y in right) ** 0.5
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def _combined_text(*, title: str, description: str) -> str:
    return f"{title.strip()}\n\n{description.strip()}"


class ScenarioSimilarityService:
    def __init__(
        self,
        *,
        scenarios_repo: ScenariosRepository,
        audit_service: AuditService,
    ) -> None:
        self._scenarios_repo = scenarios_repo
        self._audit = audit_service

    async def check(
        self,
        *,
        title: str,
        description: str,
        actor: UserModel,
        exclude_scenario_id: str | None = None,
    ) -> SimilarityCheckResult:
        query_text = _combined_text(title=title, description=description)
        if len(title.strip()) < 1 or len(description.strip()) < 1:
            return SimilarityCheckResult(candidates=[], provider="skipped")

        published = await self._scenarios_repo.list_publicly_visible()
        if exclude_scenario_id:
            published = [s for s in published if (s.id or "") != exclude_scenario_id]

        provider = "heuristic"
        candidates: list[SimilarityCandidate] = []

        api_key = (settings.openai_api_key or "").strip()
        if api_key:
            try:
                candidates = await self._embedding_candidates(
                    query_text=query_text,
                    published=published,
                    api_key=api_key,
                )
                provider = "openai_embeddings"
            except Exception:
                candidates = []

        if not candidates:
            candidates = self._heuristic_candidates(query_text=query_text, published=published)
            provider = "heuristic"

        await self._audit.record(
            actor=actor,
            action_type=AuditActionType.SCENARIO_SIMILARITY_CHECK_RUN,
            subject_type=AuditSubjectType.SCENARIO,
            subject_id=exclude_scenario_id or "",
            current={
                "provider": provider,
                "candidate_count": len(candidates),
                "candidate_ids": [c.scenario_id for c in candidates[:10]],
            },
        )
        return SimilarityCheckResult(candidates=candidates, provider=provider)

    def _heuristic_candidates(
        self,
        *,
        query_text: str,
        published: list[ScenarioModel],
    ) -> list[SimilarityCandidate]:
        scored: list[SimilarityCandidate] = []
        for scenario in published:
            other = _combined_text(
                title=scenario.public_title or scenario.title,
                description=scenario.public_description or scenario.description,
            )
            score = _heuristic_score(query_text, other)
            if score >= _HEURISTIC_MIN_SCORE:
                scored.append(
                    SimilarityCandidate(
                        scenario_id=scenario.id or "",
                        title=scenario.public_title or scenario.title,
                        score=round(score, 4),
                        public_path=_public_path_for(scenario),
                    )
                )
        scored.sort(key=lambda row: row.score, reverse=True)
        return scored[:8]

    async def _embedding_candidates(
        self,
        *,
        query_text: str,
        published: list[ScenarioModel],
        api_key: str,
    ) -> list[SimilarityCandidate]:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        model = settings.openai_embedding_model
        corpus: list[tuple[ScenarioModel, str]] = []
        for scenario in published[:40]:
            text = _combined_text(
                title=scenario.public_title or scenario.title,
                description=scenario.public_description or scenario.description,
            )
            corpus.append((scenario, text))
        if not corpus:
            return []

        inputs = [query_text, *[text for _, text in corpus]]
        response = await client.embeddings.create(model=model, input=inputs)
        vectors = [row.embedding for row in response.data]
        query_vec = vectors[0]
        scored: list[SimilarityCandidate] = []
        for (scenario, _), vec in zip(corpus, vectors[1:], strict=True):
            score = _cosine(query_vec, vec)
            if score >= _EMBEDDING_MIN_SCORE:
                scored.append(
                    SimilarityCandidate(
                        scenario_id=scenario.id or "",
                        title=scenario.public_title or scenario.title,
                        score=round(score, 4),
                        public_path=_public_path_for(scenario),
                    )
                )
        scored.sort(key=lambda row: row.score, reverse=True)
        return scored[:8]
