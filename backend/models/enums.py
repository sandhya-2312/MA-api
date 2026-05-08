from enum import Enum


class UserRole(str, Enum):
    ADMIN = "Admin"
    USER = "User"
    VIEWER = "Viewer"
