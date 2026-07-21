from __future__ import annotations

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class UserRegistered(DomainEvent):
    user_id: str = ""
    email: str = ""
    tenant_id: str = ""


@dataclass(frozen=True, slots=True)
class UserAddedToTenant(DomainEvent):
    tenant_id: str = ""
    user_id: str = ""
    role: str = ""


UserInvited = UserAddedToTenant
