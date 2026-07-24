from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATIONS = "operations"


class UserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
