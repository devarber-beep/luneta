"""Atomic permissions (RBAC) for the platform authorization policy."""
from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    SCENARIO_READ_PUBLIC = "scenario_read_public"
    SCENARIO_CREATE_DRAFT = "scenario_create_draft"
    SCENARIO_READ_OWN = "scenario_read_own"
    SCENARIO_UPDATE_OWN = "scenario_update_own"
    SCENARIO_DELETE_OWN = "scenario_delete_own"
    SCENARIO_SUBMIT_REVIEW = "scenario_submit_review"
    SCENARIO_READ_REVIEW_QUEUE = "scenario_read_review_queue"
    SCENARIO_UPDATE_IN_REVIEW = "scenario_update_in_review"
    SCENARIO_REJECT = "scenario_reject"
    SCENARIO_PUBLISH = "scenario_publish"
    USER_READ_SELF = "user_read_self"
    USER_UPDATE_SELF = "user_update_self"
    AUDIT_EVENT_CREATE = "audit_event_create"
