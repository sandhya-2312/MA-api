from backend.models.enums import UserRole


def normalize_role(role: UserRole | str | None) -> str:
    if role is None:
        return ""

    if isinstance(role, UserRole):
        return role.value

    value = str(role).strip()
    if not value:
        return ""

    lowered = value.lower()
    for member in UserRole:
        if lowered in {member.value.lower(), member.name.lower()}:
            return member.value

    return value


def to_user_role(role: UserRole | str | None) -> UserRole | None:
    normalized = normalize_role(role)
    for member in UserRole:
        if member.value == normalized:
            return member
    return None


def is_admin_role(role: UserRole | str | None) -> bool:
    return normalize_role(role) == UserRole.ADMIN.value
