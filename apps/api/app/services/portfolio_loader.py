"""Load reviewer portfolio investigator ids for scenario authorization."""
from __future__ import annotations

from app.domain.enums import UserRole
from app.models.user import UserModel
from app.repositories.reviewer_assignments import ReviewerAssignmentsRepository


async def portfolio_investigator_ids_for_user(
    *,
    user: UserModel,
    assignments_repo: ReviewerAssignmentsRepository,
) -> frozenset[str]:
    if UserRole(user.role) != UserRole.REVIEWER:
        return frozenset()
    ids = await assignments_repo.list_investigator_ids_for_reviewer(user.id or "")
    return frozenset(ids)
