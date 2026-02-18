from luneta.core.rbac import Role, user_has_role


def test_user_has_role() -> None:
    roles = [Role.MEMBER, Role.REVIEWER]
    assert user_has_role(roles, Role.MEMBER)
    assert not user_has_role(roles, Role.ORG_ADMIN)

