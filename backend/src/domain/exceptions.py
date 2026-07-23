"""Domain exceptions."""


class DomainError(Exception):
    """Base domain error."""


class TenantAlreadySuspended(DomainError):
    def __init__(self, message: str = "Tenant is already suspended.") -> None:
        super().__init__(message)


class TenantNotSuspended(DomainError):
    def __init__(self, message: str = "Tenant is not suspended.") -> None:
        super().__init__(message)


class TenantNotFound(DomainError):
    def __init__(self, message: str = "Tenant not found.") -> None:
        super().__init__(message)


class TenantSuspended(DomainError):
    def __init__(self, message: str = "Tenant is suspended.") -> None:
        super().__init__(message)


class InviteNotFound(DomainError):
    def __init__(self, message: str = "Invite not found.") -> None:
        super().__init__(message)


class InviteExpired(DomainError):
    def __init__(self, message: str = "Invite expired.") -> None:
        super().__init__(message)


class InviteNotPending(DomainError):
    def __init__(self, message: str = "Invite not found.") -> None:
        super().__init__(message)


class UserInactive(DomainError):
    def __init__(self, message: str = "User is inactive.") -> None:
        super().__init__(message)


class UserNotFound(DomainError):
    def __init__(self, message: str = "User not found.") -> None:
        super().__init__(message)


class DuplicateEmail(DomainError):
    def __init__(self, message: str = "Email already exists.") -> None:
        super().__init__(message)


class DuplicateUsername(DomainError):
    def __init__(self, message: str = "Username already exists.") -> None:
        super().__init__(message)


class DuplicateTenantSlug(DomainError):
    def __init__(self, message: str = "Tenant slug already exists.") -> None:
        super().__init__(message)


class RegistrationClosed(DomainError):
    def __init__(self, message: str = "Registration is closed. Contact an administrator.") -> None:
        super().__init__(message)


class InvalidCredentials(DomainError):
    def __init__(self, message: str = "Invalid credentials.") -> None:
        super().__init__(message)


class InvalidToken(DomainError):
    def __init__(self, message: str = "Invalid refresh token.") -> None:
        super().__init__(message)


class MembershipInactive(DomainError):
    def __init__(self, message: str = "Membership inactive or missing.") -> None:
        super().__init__(message)


class Forbidden(DomainError):
    def __init__(self, message: str = "Forbidden.") -> None:
        super().__init__(message)


class InvalidRoleCode(DomainError):
    def __init__(self, message: str = "Invalid role_code.") -> None:
        super().__init__(message)
