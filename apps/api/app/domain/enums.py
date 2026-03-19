"""Domain enums for vertical slice workflow."""
from enum import StrEnum


class UserRole(StrEnum):
    AUTHOR = "author"
    REVIEWER = "reviewer"


class ScenarioState(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PUBLISHED = "published"


class ReviewEventType(StrEnum):
    DRAFT_SAVED = "draft_saved"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PUBLISHED = "published"
