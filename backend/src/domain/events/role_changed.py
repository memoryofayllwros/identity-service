from __future__ import annotations

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class RoleChanged(DomainEvent):
    tenant_id: str = ""
    user_id: str = ""
    role_ids: tuple[str, ...] = ()
