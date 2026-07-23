from __future__ import annotations

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class TenantActivated(DomainEvent):
    tenant_id: str = ""
