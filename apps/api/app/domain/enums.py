"""Domain enums for vertical slice workflow."""
from enum import StrEnum


class UserRole(StrEnum):
    INVESTIGATOR = "investigator"
    COORDINATOR = "coordinator"


class UserAccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ScenarioState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"


class CollaboratorRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"


class ReviewEventType(StrEnum):
    CREATE_DRAFT = "create_draft"
    DRAFT_SAVED = "draft_saved"
    SUBMITTED = "submitted"
    UPDATE_IN_REVIEW = "update_in_review"
    REJECTED = "rejected"
    PUBLISHED = "published"
    COLLABORATOR_ADDED = "collaborator_added"
    COLLABORATOR_REMOVED = "collaborator_removed"
