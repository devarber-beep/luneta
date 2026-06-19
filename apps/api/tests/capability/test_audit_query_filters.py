"""Audit query filter resolution."""
from __future__ import annotations

import re

import pytest
from bson import ObjectId

from app.domain.enums import AuditSubjectType
from app.repositories.audit_events import AuditEventsRepository
from app.repositories.scenarios import ScenariosRepository
from app.repositories.users import UsersRepository
from app.services.audit_service import AuditQueryService
from tests.conftest import FakeDB, _matches, user_doc


@pytest.mark.asyncio
async def test_list_ids_matching_title_on_fake_db() -> None:
    db = FakeDB()
    oid = ObjectId()
    scenario_id = str(oid)
    doc = {
        "_id": oid,
        "title": "Classroom VR ethics scenario",
        "deleted_at": None,
    }
    await db["scenarios"].insert_one(doc)
    pattern = re.escape("Classroom VR")
    query = {
        "deleted_at": None,
        "$or": [
            {"title": {"$regex": pattern, "$options": "i"}},
            {"public_title": {"$regex": pattern, "$options": "i"}},
        ],
    }
    assert _matches(doc, query)
    ids = await ScenariosRepository(db).list_ids_matching_title("Classroom VR")
    assert ids == [scenario_id]


@pytest.mark.asyncio
async def test_subject_query_matches_scenario_title() -> None:
    db = FakeDB()
    oid = ObjectId()
    scenario_id = str(oid)
    await db["scenarios"].insert_one(
        {
            "_id": oid,
            "title": "Classroom VR ethics scenario",
            "slug": "classroom-vr",
            "description": "Body",
            "state": "published",
            "deleted_at": None,
        }
    )
    await db["audit_events"].insert_one(
        {
            "actor_user_id": "actor-1",
            "actor_role": "admin",
            "action_type": "scenario_published",
            "subject_type": "scenario",
            "subject_id": scenario_id,
            "previous": None,
            "current": {"state": "published"},
            "created_at": "2026-01-01T00:00:00Z",
        }
    )

    service = AuditQueryService(
        audit_repo=AuditEventsRepository(db),
        users_repo=UsersRepository(db),
        scenarios_repo=ScenariosRepository(db),
    )
    items, total = await service.list_events_enriched(
        subject_type=AuditSubjectType.SCENARIO,
        subject_query="Classroom VR",
    )
    assert total == 1
    assert items[0]["subject_display_label"] == "Classroom VR ethics scenario"


@pytest.mark.asyncio
async def test_actor_query_matches_email() -> None:
    db = FakeDB()
    insert = await db["users"].insert_one(
        user_doc(email="actor-audit@luneta.dev", role="admin", password_plain="x")
    )
    actor_id = str(insert.inserted_id)
    await db["audit_events"].insert_one(
        {
            "actor_user_id": actor_id,
            "actor_role": "admin",
            "action_type": "scenario_created",
            "subject_type": "scenario",
            "subject_id": "sc-1",
            "previous": None,
            "current": None,
            "created_at": "2026-01-01T00:00:00Z",
        }
    )

    service = AuditQueryService(
        audit_repo=AuditEventsRepository(db),
        users_repo=UsersRepository(db),
        scenarios_repo=ScenariosRepository(db),
    )
    items, total = await service.list_events_enriched(actor_query="actor-audit@luneta.dev")
    assert total == 1
    assert items[0]["actor_user_id"] == actor_id
