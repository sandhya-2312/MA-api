from backend.models.enums import UserRole

ROLE_PERMISSIONS = {
    UserRole.ADMIN.value: {
        "users:create",
        "users:read",
        "users:update",
        "users:delete",
        "projects:create",
        "projects:read",
        "projects:update",
        "projects:delete",
        "projects:assign",
        "data:create",
        "data:update",
        "dashboard:read",
        "profile:update",
    },
    UserRole.USER.value: {
        "projects:read_assigned",
        "data:create",
        "data:update_assigned",
        "dashboard:read_assigned",
        "profile:update",
    },
    UserRole.VIEWER.value: {
        "projects:read_assigned",
        "dashboard:read_assigned",
        "profile:update",
    },
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
