"""Backward-compatible event type re-exports."""

from src.domain.events import (
    DomainEvent,
    TenantCreated,
    UserAddedToTenant,
    UserInvited,
)

__all__ = ["DomainEvent", "TenantCreated", "UserAddedToTenant", "UserInvited"]
