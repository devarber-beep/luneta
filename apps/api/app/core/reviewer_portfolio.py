"""Portfolio checks for reviewer scenario access."""
from __future__ import annotations

from app.domain.enums import UserRole
from app.models.user import UserModel


def reviewer_has_investigator_in_portfolio(
    *,
    user: UserModel,
    investigator_user_id: str,
    portfolio_investigator_ids: frozenset[str],
) -> bool:
    if UserRole(user.role) == UserRole.ADMIN:
        return True
    if UserRole(user.role) != UserRole.REVIEWER:
        return False
    return investigator_user_id in portfolio_investigator_ids
