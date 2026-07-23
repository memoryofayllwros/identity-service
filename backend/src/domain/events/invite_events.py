from __future__ import annotations

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class InviteRevoked(DomainEvent):
    invite_id: str = ""
    tenant_id: str = ""
