"""Domain exceptions."""


class DomainError(Exception):
    """Base domain error."""


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


class RegistrationClosed(DomainError):
    def __init__(self, message: str = "Registration is closed. Contact an administrator.") -> None:
        super().__init__(message)


class InvalidCredentials(DomainError):
    def __init__(self, message: str = "Invalid credentials.") -> None:
        super().__init__(message)


class InvalidToken(DomainError):
    def __init__(self, message: str = "Invalid refresh token.") -> None:
        super().__init__(message)


class Forbidden(DomainError):
    def __init__(self, message: str = "Forbidden.") -> None:
        super().__init__(message)


class InvalidRoleCode(DomainError):
    def __init__(self, message: str = "Invalid role_code.") -> None:
        super().__init__(message)


class TenantNotFound(DomainError):
    def __init__(self, message: str = "Company not found.") -> None:
        super().__init__(message)


class TenantSuspended(DomainError):
    def __init__(self, message: str = "Company account is suspended.") -> None:
        super().__init__(message)
