"""Unit test for vertical slice happy path with in-memory fakes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.enums import ReviewEventType, ScenarioState, UserRole
from app.models.scenario import ScenarioModel
from app.models.user import UserModel
from app.schemas.workflow import ReviewQueueItem
from app.services.scenario_service import ScenarioService
from app.services.workflow_service import WorkflowService


@dataclass
class _FakeScenariosRepo:
    scenario: ScenarioModel | None = None
    id_seq: int = 1

    async def ensure_indexes(self) -> None:
        return None

    async def create(self, *, slug: str, title: str, body_markdown: str, author_user_id: str) -> ScenarioModel:
        now = datetime.now(UTC)
        self.scenario = ScenarioModel(
            _id=str(self.id_seq),
            slug=slug,
            title=title,
            body_markdown=body_markdown,
            author_user_id=author_user_id,
            state=ScenarioState.DRAFT,
            current_revision_number=1,
            created_at=now,
            updated_at=now,
        )
        return self.scenario

    async def get_by_id(self, scenario_id: str) -> ScenarioModel | None:
        if self.scenario and self.scenario.id == scenario_id:
            return self.scenario
        return None

    async def update_draft_content(self, *, scenario_id: str, title: str | None, body_markdown: str | None):
        if not self.scenario or self.scenario.id != scenario_id:
            return None
        data = self.scenario.model_dump()
        if title is not None:
            data["title"] = title
        if body_markdown is not None:
            data["body_markdown"] = body_markdown
        data["updated_at"] = datetime.now(UTC)
        self.scenario = ScenarioModel.model_validate(data)
        return self.scenario

    async def bump_revision_number(self, *, scenario_id: str):
        if not self.scenario or self.scenario.id != scenario_id:
            return None
        data = self.scenario.model_dump()
        data["current_revision_number"] += 1
        data["updated_at"] = datetime.now(UTC)
        self.scenario = ScenarioModel.model_validate(data)
        return self.scenario

    async def set_state(self, *, scenario_id: str, state: ScenarioState):
        if not self.scenario or self.scenario.id != scenario_id:
            return None
        data = self.scenario.model_dump()
        data["state"] = state
        data["updated_at"] = datetime.now(UTC)
        if state == ScenarioState.PUBLISHED:
            data["published_at"] = datetime.now(UTC)
        self.scenario = ScenarioModel.model_validate(data)
        return self.scenario

    async def list_by_state(self, *, state: ScenarioState) -> list[ScenarioModel]:
        if self.scenario and self.scenario.state == state:
            return [self.scenario]
        return []


@dataclass
class _FakeRevisionsRepo:
    snapshots: list[dict] = None

    def __post_init__(self) -> None:
        self.snapshots = []

    async def ensure_indexes(self) -> None:
        return None

    async def create_snapshot(self, **kwargs):
        self.snapshots.append(kwargs)
        return kwargs


@dataclass
class _FakeReviewEventsRepo:
    events: list[dict] = None

    def __post_init__(self) -> None:
        self.events = []

    async def ensure_indexes(self) -> None:
        return None

    async def create(self, **kwargs):
        self.events.append(kwargs)
        return kwargs


def _author() -> UserModel:
    now = datetime.now(UTC)
    return UserModel(
        _id="author-1",
        email="author@luneta.dev",
        password_hash="x",
        role=UserRole.AUTHOR,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )


def _reviewer() -> UserModel:
    now = datetime.now(UTC)
    return UserModel(
        _id="reviewer-1",
        email="reviewer@luneta.dev",
        password_hash="x",
        role=UserRole.REVIEWER,
        is_email_verified=True,
        created_at=now,
        updated_at=now,
    )


async def test_vertical_slice_happy_path_unit() -> None:
    scenarios_repo = _FakeScenariosRepo()
    revisions_repo = _FakeRevisionsRepo()
    review_events_repo = _FakeReviewEventsRepo()

    scenario_service = ScenarioService(
        scenarios_repo=scenarios_repo,
        revisions_repo=revisions_repo,
        review_events_repo=review_events_repo,
    )
    workflow_service = WorkflowService(
        scenarios_repo=scenarios_repo,
        review_events_repo=review_events_repo,
    )

    author = _author()
    reviewer = _reviewer()

    created = await scenario_service.create_draft(
        current_user=author,
        slug="mi-escenario",
        title="Mi escenario",
        body_markdown="Version 1",
    )
    assert created.state == ScenarioState.DRAFT

    edited = await scenario_service.patch_draft(
        scenario_id=created.id or "",
        current_user=author,
        title="Mi escenario editado",
        body_markdown="Version 2",
    )
    assert edited.current_revision_number == 2

    submitted = await scenario_service.submit_review(
        scenario_id=created.id or "",
        current_user=author,
    )
    assert submitted.state == ScenarioState.IN_REVIEW

    queue: list[ReviewQueueItem] = await workflow_service.review_queue(current_user=reviewer)
    assert len(queue) == 1

    approved, _ = await workflow_service.approve(
        scenario_id=created.id or "",
        current_user=reviewer,
    )
    assert approved.state == ScenarioState.APPROVED

    published, _ = await workflow_service.publish(
        scenario_id=created.id or "",
        current_user=reviewer,
    )
    assert published.state == ScenarioState.PUBLISHED

    event_types = [event["event_type"] for event in review_events_repo.events]
    assert ReviewEventType.DRAFT_SAVED in event_types
    assert ReviewEventType.SUBMITTED in event_types
    assert ReviewEventType.APPROVED in event_types
    assert ReviewEventType.PUBLISHED in event_types
