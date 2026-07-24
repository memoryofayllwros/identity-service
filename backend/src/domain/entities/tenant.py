from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.entities._base import AggregateRoot
from src.domain.enums import TenantStatus
from src.domain.events.tenant_created import TenantCreated
from src.domain.utils import now_hk


@dataclass
class Tenant(AggregateRoot):
    """Single company profile stored for this deployment."""

    id: str
    name: str
    slug: str
    status: TenantStatus = TenantStatus.ACTIVE
    features: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        name: str,
        slug: str,
        features: list[str] | None = None,
    ) -> Tenant:
        tenant = cls(
            id=tenant_id,
            name=name,
            slug=slug,
            features=list(features or []),
            created_at=now_hk(),
        )
        tenant._record(
            TenantCreated(
                tenant_id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
            )
        )
        return tenant

    @property
    def is_suspended(self) -> bool:
        return self.status == TenantStatus.SUSPENDED or not self.is_active

    def update_profile(
        self,
        *,
        name: str | None = None,
        features: list[str] | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if features is not None:
            self.features = list(features)
        self.updated_at = now_hk()
