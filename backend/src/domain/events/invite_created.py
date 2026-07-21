from __future__ import annotations

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class InviteCreated(DomainEvent):
    invite_id: str = ""
    tenant_id: str = ""
    email: str = ""


@dataclass(frozen=True, slots=True)
class InviteAccepted(DomainEvent):
    invite_id: str = ""
    tenant_id: str = ""
    user_id: str = ""
