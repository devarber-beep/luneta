from enum import Enum


class Role(str, Enum):
    MEMBER = "member"
    REVIEWER = "reviewer"
    ORG_ADMIN = "org_admin"
    PLATFORM_ADMIN = "platform_admin"


def user_has_role(user_roles: list[Role], required: Role) -> bool:
    return required in user_roles

