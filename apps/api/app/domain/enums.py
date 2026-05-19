"""Enumerations shared by domain logic, persistence models, and events."""
from enum import StrEnum


class UserRole(StrEnum):
    REGISTERED = "registered"
    INVESTIGATOR = "investigator"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class UserAccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ScenarioState(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    IN_REVIEW = "in_review"
    CHANGES_REQUIRED = "changes_required"
    APPLYING_CHANGES = "applying_changes"
    PUBLISHED = "published"
    NOT_SUITABLE = "not_suitable"


class ReviewOutcome(StrEnum):
    PUBLISHED = "published"
    CHANGES_REQUIRED = "changes_required"
    NOT_SUITABLE = "not_suitable"


class CollaboratorRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"


class ReviewEventType(StrEnum):
    CREATE_DRAFT = "create_draft"
    DRAFT_SAVED = "draft_saved"
    SUBMITTED = "submitted"
    UPDATE_IN_REVIEW = "update_in_review"
    REVIEW_STARTED = "review_started"
    CHANGES_REQUESTED = "changes_requested"
    APPLYING_CHANGES_STARTED = "applying_changes_started"
    MARKED_NOT_SUITABLE = "marked_not_suitable"
    REOPENED_FROM_NOT_SUITABLE = "reopened_from_not_suitable"
    PUBLISHED = "published"
    COLLABORATOR_ADDED = "collaborator_added"
    COLLABORATOR_REMOVED = "collaborator_removed"


class AuditSubjectType(StrEnum):
    USER = "user"
    SCENARIO = "scenario"
    SUGGESTION = "suggestion"
    EVALUATION = "evaluation"
    CLASSIFICATION_ENTRY = "classification_entry"
    ETHICAL_RISK_ENTRY = "ethical_risk_entry"


class AuditActionType(StrEnum):
    INVESTIGATOR_ACCOUNT_CREATED = "investigator_account_created"
    USER_ROLE_CHANGED = "user_role_changed"
    USER_ACCOUNT_STATUS_CHANGED = "user_account_status_changed"
    REVIEWER_ASSIGNMENT_CREATED = "reviewer_assignment_created"
    REVIEWER_ASSIGNMENT_REMOVED = "reviewer_assignment_removed"
    EVALUATION_MODERATED = "evaluation_moderated"
