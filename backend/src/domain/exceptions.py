"""Domain exceptions."""


class DomainError(Exception):
    """Base domain error."""


class TenantAlreadySuspended(DomainError):
    pass


class TenantNotSuspended(DomainError):
    pass


class InviteNotFound(DomainError):
    pass


class InviteExpired(DomainError):
    pass


class InviteNotPending(DomainError):
    pass


class UserInactive(DomainError):
    pass


class DuplicateEmail(DomainError):
    pass


class DuplicateUsername(DomainError):
    pass


class RegistrationClosed(DomainError):
    pass
