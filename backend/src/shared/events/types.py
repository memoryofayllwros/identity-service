"""In-process domain event types (Identity service only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.models._utils import as_hk


@dataclass(frozen=True, slots=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=as_hk)

    def to_dict(self) -> dict[str, Any]:
        return {"type": type(self).__name__, "occurred_at": self.occurred_at.isoformat()}


@dataclass(frozen=True, slots=True)
class TenantCreated(DomainEvent):
    tenant_id: str = ""
    name: str = ""
    slug: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "tenant_id": self.tenant_id,
            "name": self.name,
            "slug": self.slug,
        }


@dataclass(frozen=True, slots=True)
class UserInvited(DomainEvent):
    tenant_id: str = ""
    user_id: str = ""
    role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            **super().to_dict(),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "role": self.role,
        }


UserAddedToTenant = UserInvited
