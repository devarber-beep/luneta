"""Domain enums for vertical slice workflow."""
from enum import StrEnum


class UserRole(StrEnum):
    AUTHOR = "author"
    REVIEWER = "reviewer"


class UserAccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class ScenarioState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"


class CollaboratorRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"


class ReviewEventType(StrEnum):
    DRAFT_SAVED = "draft_saved"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PUBLISHED = "published"
    COLLABORATOR_ADDED = "collaborator_added"
    COLLABORATOR_REMOVED = "collaborator_removed"
