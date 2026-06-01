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
    COLLABORATOR = "collaborator"


class SuggestionScope(StrEnum):
    SCENARIO = "scenario"
    PARAGRAPH = "paragraph"


class SuggestionKind(StrEnum):
    COMMENT = "comment"
    ALTERNATIVE_TEXT = "alternative_text"


class SuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class EvaluationVisibility(StrEnum):
    VISIBLE = "visible"
    HIDDEN = "hidden"


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
    SUGGESTION_ACCEPTED = "suggestion_accepted"


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
    EVALUATION_SUBMITTED = "evaluation_submitted"
    EVALUATION_MODERATED = "evaluation_moderated"
    SUGGESTION_CREATED = "suggestion_created"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    SUGGESTION_REJECTED = "suggestion_rejected"
    SENSITIVE_DATA_CHECK_RUN = "sensitive_data_check_run"
    SCENARIO_SIMILARITY_CHECK_RUN = "scenario_similarity_check_run"
    SCENARIO_CREATED = "scenario_created"
    SCENARIO_SUBMITTED_FOR_REVIEW = "scenario_submitted_for_review"
    SCENARIO_PUBLISHED = "scenario_published"
    SCENARIO_CHANGES_REQUESTED = "scenario_changes_requested"
    SCENARIO_MARKED_NOT_SUITABLE = "scenario_marked_not_suitable"
    SCENARIO_REOPENED = "scenario_reopened"
    SCENARIO_DRAFT_DELETED = "scenario_draft_deleted"
    SCENARIO_COLLABORATOR_ADDED = "scenario_collaborator_added"
    SCENARIO_COLLABORATOR_REMOVED = "scenario_collaborator_removed"


class NotificationEntityType(StrEnum):
    SCENARIO = "scenario"
    SUGGESTION = "suggestion"
    USER = "user"
    EVALUATION = "evaluation"


class NotificationType(StrEnum):
    SUGGESTION_RECEIVED = "suggestion_received"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    SUGGESTION_REJECTED = "suggestion_rejected"
    SCENARIO_SUBMITTED_FOR_REVIEW = "scenario_submitted_for_review"
    SCENARIO_REVIEW_PUBLISHED = "scenario_review_published"
    SCENARIO_REVIEW_CHANGES_REQUIRED = "scenario_review_changes_required"
    SCENARIO_REVIEW_NOT_SUITABLE = "scenario_review_not_suitable"
    SCENARIO_REOPENED = "scenario_reopened"
    COLLABORATOR_ADDED = "collaborator_added"
    INVESTIGATOR_INVITED = "investigator_invited"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_REACTIVATED = "account_reactivated"
    USER_ROLE_CHANGED = "user_role_changed"
    SCENARIO_EVALUATION_RECEIVED = "scenario_evaluation_received"
    PASSWORD_CHANGED = "password_changed"
