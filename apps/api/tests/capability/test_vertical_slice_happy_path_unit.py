"""Unit test for vertical slice happy path with in-memory fakes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.enums import ReviewEventType, ScenarioState, UserAccountStatus, UserRole
from app.models.scenario import ScenarioModel, slugify_title
from app.models.user import UserModel
from app.schemas.workflow import ReviewQueueItem
from app.services.mailer_service import NoopMailer
from app.services.scenario_service import ScenarioService
from app.services.workflow_service import WorkflowService


@dataclass
class _FakeScenariosRepo:
    scenario: ScenarioModel | None = None
    id_seq: int = 1

    async def ensure_indexes(self) -> None:
        return None

    async def create(self, *, title: str, description: str, author_user_id: str) -> ScenarioModel:
        now = datetime.now(UTC)
        self.scenario = ScenarioModel(
            _id=str(self.id_seq),
            slug=slugify_title(title),
            title=title,
            description=description,
            author_user_id=author_user_id,
            state=ScenarioState.DRAFT,
            current_revision_number=1,
            last_state_changed_at=now,
            created_at=now,
            updated_at=now,
        )
        return self.scenario

    async def get_by_id(self, scenario_id: str) -> ScenarioModel | None:
        if self.scenario and self.scenario.id == scenario_id:
            return self.scenario
        return None

    async def update_draft_content(
        self,
        *,
        scenario_id: str,
        title: str | None,
        description: str | None,
        summary: str | None,
        categories: list[str] | None,
        tags: list[str] | None,
        category_ids: list[str] | None = None,
        ethical_risk_ids: list[str] | None = None,
        sensitive_data_involved: bool | None = None,
    ):
        if not self.scenario or self.scenario.id != scenario_id:
            return None
        data = self.scenario.model_dump()
        if title is not None:
            data["title"] = title
            data["slug"] = slugify_title(title)[:80]
        if description is not None:
            data["description"] = description
        if category_ids is not None:
            data["category_ids"] = category_ids
        if ethical_risk_ids is not None:
            data["ethical_risk_ids"] = ethical_risk_ids
        if summary is not None:
            data["summary"] = summary
        if categories is not None:
            data["categories"] = categories
        if tags is not None:
            data["tags"] = tags
        if sensitive_data_involved is not None:
            data["sensitive_data_involved"] = sensitive_data_involved
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

    async def set_state(self, *, scenario_id: str, state: ScenarioState, actor_user_id: str):
        if not self.scenario or self.scenario.id != scenario_id:
            return None
        data = self.scenario.model_dump()
        data["state"] = state
        data["last_state_changed_at"] = datetime.now(UTC)
        data["updated_at"] = datetime.now(UTC)
        if state == ScenarioState.QUEUED:
            data["submitted_for_review_at"] = datetime.now(UTC)
            data["submitted_for_review_by_user_id"] = actor_user_id
        if state == ScenarioState.IN_REVIEW:
            data["review_started_at"] = datetime.now(UTC)
        if state == ScenarioState.PUBLISHED:
            now = datetime.now(UTC)
            data["published_at"] = now
            data["approved_at"] = now
            data["approved_by_user_id"] = actor_user_id
            if data.get("first_published_at") is None:
                data["first_published_at"] = now
            if data.get("first_approved_at") is None:
                data["first_approved_at"] = now
            data["published_by_user_id"] = actor_user_id
            data["public_title"] = data.get("title")
            data["public_description"] = data.get("description")
            data["public_slug"] = data.get("slug")
            data["public_revision_number"] = data.get("current_revision_number")
        self.scenario = ScenarioModel.model_validate(data)
        return self.scenario

    async def submit_to_queue(self, *, scenario_id: str, actor_user_id: str):
        return await self.set_state(
            scenario_id=scenario_id, state=ScenarioState.QUEUED, actor_user_id=actor_user_id
        )

    async def start_review(self, *, scenario_id: str):
        return await self.set_state(scenario_id=scenario_id, state=ScenarioState.IN_REVIEW, actor_user_id="")

    async def list_by_state(self, *, state: ScenarioState) -> list[ScenarioModel]:
        return await self.list_by_states(states=[state])

    async def list_by_states(self, *, states: list[ScenarioState], **kwargs) -> list[ScenarioModel]:
        if self.scenario and self.scenario.state in states:
            return [self.scenario]
        return []

    async def list_reviewed(self, **kwargs) -> list[ScenarioModel]:
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


@dataclass
class _FakeUsersRepo:
    users: dict[str, UserModel] = None

    def __post_init__(self) -> None:
        self.users = {}

    async def get_by_id(self, user_id: str) -> UserModel | None:
        return self.users.get(user_id)

    async def list_verified_emails_by_role(self, role: str) -> list[str]:
        return await self.list_verified_emails_by_roles([role])

    async def list_verified_emails_by_roles(self, roles: list[str]) -> list[str]:
        role_set = set(roles)
        return [
            str(u.email_normalized)
            for u in self.users.values()
            if str(u.role) in role_set
            and u.email_verified_at is not None
            and u.account_status == UserAccountStatus.ACTIVE
        ]


def _author() -> UserModel:
    now = datetime.now(UTC)
    return UserModel(
        _id="author-1",
        email_normalized="author@luneta.dev",
        password_hash="x",
        password_updated_at=now,
        role=UserRole.INVESTIGATOR,
        email_verified_at=now,
        nickname="author",
        nickname_normalized="author",
        created_at=now,
        updated_at=now,
    )


def _reviewer() -> UserModel:
    now = datetime.now(UTC)
    return UserModel(
        _id="reviewer-1",
        email_normalized="reviewer@luneta.dev",
        password_hash="x",
        password_updated_at=now,
        role=UserRole.REVIEWER,
        email_verified_at=now,
        nickname="reviewer",
        nickname_normalized="reviewer",
        created_at=now,
        updated_at=now,
    )


class _FakeAssignmentsRepo:
    def __init__(self, mapping: dict[str, list[str]]) -> None:
        self._mapping = mapping

    async def list_investigator_ids_for_reviewer(self, reviewer_user_id: str) -> list[str]:
        return list(self._mapping.get(reviewer_user_id, []))


class _FakeClassificationRepo:
    async def ensure_indexes(self) -> None:
        return None

    async def get_by_id(self, entry_id: str):
        from app.models.scenario_classification import ScenarioClassificationEntryModel

        now = datetime.now(UTC)
        if entry_id == "cat-1":
            return ScenarioClassificationEntryModel(
                _id="cat-1",
                slug="cat",
                label="Category",
                is_active=True,
                sort_order=0,
                created_at=now,
                updated_at=now,
            )
        return None

    async def list_active(self):
        from app.models.scenario_classification import ScenarioClassificationEntryModel

        now = datetime.now(UTC)
        return [
            ScenarioClassificationEntryModel(
                _id="cat-1",
                slug="cat",
                label="Category",
                is_active=True,
                sort_order=0,
                created_at=now,
                updated_at=now,
            )
        ]


class _FakeEthicalRepo:
    async def ensure_indexes(self) -> None:
        return None

    async def list_active(self):
        from app.models.ethical_risk import EthicalRiskEntryModel

        now = datetime.now(UTC)
        return [
            EthicalRiskEntryModel(
                _id="risk-1",
                slug="risk",
                label="Risk",
                is_active=True,
                sort_order=0,
                created_at=now,
                updated_at=now,
            )
        ]


async def test_vertical_slice_happy_path_unit() -> None:
    scenarios_repo = _FakeScenariosRepo()
    revisions_repo = _FakeRevisionsRepo()
    review_events_repo = _FakeReviewEventsRepo()
    users_repo = _FakeUsersRepo()
    noop_mailer = NoopMailer()
    author = _author()
    reviewer = _reviewer()
    assignments_repo = _FakeAssignmentsRepo({reviewer.id or "": [author.id or ""]})
    classification_repo = _FakeClassificationRepo()
    ethical_repo = _FakeEthicalRepo()
    scenario_service = ScenarioService(
        scenarios_repo=scenarios_repo,
        revisions_repo=revisions_repo,
        review_events_repo=review_events_repo,
        users_repo=users_repo,
        assignments_repo=assignments_repo,
        classification_repo=classification_repo,
        ethical_repo=ethical_repo,
        mailer=noop_mailer,
    )
    workflow_service = WorkflowService(
        scenarios_repo=scenarios_repo,
        review_events_repo=review_events_repo,
        users_repo=users_repo,
        assignments_repo=assignments_repo,
        mailer=noop_mailer,
    )

    users_repo.users[author.id or ""] = author
    users_repo.users[reviewer.id or ""] = reviewer

    created = await scenario_service.create_draft(
        current_user=author,
        title="Mi escenario",
        description="Scenario description for review",
    )
    assert created.state == ScenarioState.DRAFT

    edited = await scenario_service.patch_draft(
        scenario_id=created.id or "",
        current_user=author,
        title="Mi escenario editado",
        description="Scenario description for review (edited)",
    )
    assert edited.current_revision_number == 2

    assert scenarios_repo.scenario is not None
    ready = scenarios_repo.scenario.model_dump()
    ready["cover_image"] = {
        "asset_id": "cover-1",
        "storage_key": "scenarios/x/cover",
        "mime_type": "image/png",
        "order": 0,
    }
    ready["category_ids"] = ["cat-1"]
    ready["ethical_risk_ids"] = ["risk-1"]
    scenarios_repo.scenario = ScenarioModel.model_validate(ready)

    submitted = await scenario_service.submit_review(
        scenario_id=created.id or "",
        current_user=author,
    )
    assert submitted.state == ScenarioState.QUEUED

    queue: list[ReviewQueueItem] = await workflow_service.review_queue(current_user=reviewer)
    assert len(queue) == 1
    assert queue[0].title == "Mi escenario editado"

    in_review, _ = await workflow_service.start_review(
        scenario_id=created.id or "",
        current_user=reviewer,
    )
    assert in_review.state == ScenarioState.IN_REVIEW

    published, _ = await workflow_service.publish(
        scenario_id=created.id or "",
        current_user=reviewer,
    )
    assert published.state == ScenarioState.PUBLISHED

    rev_after_publish = published.current_revision_number
    patched_live = await scenario_service.patch_draft(
        scenario_id=created.id or "",
        current_user=author,
        title="Titulo tras publicar",
        description="Descripcion tras publicar",
    )
    assert patched_live.title == "Titulo tras publicar"
    assert patched_live.current_revision_number == rev_after_publish + 1
    assert patched_live.state == ScenarioState.PUBLISHED

    resubmitted = await scenario_service.submit_review(
        scenario_id=created.id or "",
        current_user=author,
    )
    assert resubmitted.state == ScenarioState.QUEUED

    await workflow_service.start_review(scenario_id=created.id or "", current_user=reviewer)

    republished, _ = await workflow_service.publish(
        scenario_id=created.id or "",
        current_user=reviewer,
    )
    assert republished.state == ScenarioState.PUBLISHED

    event_types = [event["event_type"] for event in review_events_repo.events]
    assert ReviewEventType.CREATE_DRAFT in event_types
    assert ReviewEventType.DRAFT_SAVED in event_types
    assert event_types.count(ReviewEventType.SUBMITTED) == 2
    assert event_types.count(ReviewEventType.PUBLISHED) == 2
