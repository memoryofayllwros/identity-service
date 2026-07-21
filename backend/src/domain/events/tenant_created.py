from __future__ import annotations

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class TenantCreated(DomainEvent):
    tenant_id: str = ""
    name: str = ""
    slug: str = ""


@dataclass(frozen=True, slots=True)
class TenantSuspended(DomainEvent):
    tenant_id: str = ""
    reason: str | None = None
