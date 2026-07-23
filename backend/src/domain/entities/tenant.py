from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.entities._base import AggregateRoot
from src.domain.enums import TenantStatus
from src.domain.events import TenantActivated, TenantCreated, TenantSuspended
from src.domain.exceptions import TenantAlreadySuspended, TenantNotSuspended
from src.domain.utils import now_hk


@dataclass
class Tenant(AggregateRoot):
    id: str
    name: str
    slug: str
    plan: str = "enterprise"
    status: TenantStatus = TenantStatus.ACTIVE
    features: list[str] = field(default_factory=list)
    is_active: bool = True
    perm_ver: int = 1
    created_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        name: str,
        slug: str,
        plan: str = "enterprise",
        features: list[str] | None = None,
        perm_ver: int = 1,
    ) -> Tenant:
        tenant = cls(
            id=tenant_id,
            name=name,
            slug=slug,
            plan=plan,
            status=TenantStatus.ACTIVE,
            features=list(features or []),
            is_active=True,
            perm_ver=perm_ver,
        )
        tenant._record(
            TenantCreated(tenant_id=tenant_id, name=name, slug=slug)
        )
        return tenant

    def suspend(self, reason: str | None = None) -> None:
        if self.status == TenantStatus.SUSPENDED:
            raise TenantAlreadySuspended()
        self.status = TenantStatus.SUSPENDED
        self.is_active = False
        self.suspended_at = now_hk()
        self._record(TenantSuspended(tenant_id=self.id, reason=reason))

    def activate(self, features: list[str] | None = None) -> None:
        if self.status == TenantStatus.ACTIVE and self.is_active:
            return
        self.status = TenantStatus.ACTIVE
        self.is_active = True
        self.suspended_at = None
        if features is not None:
            self.features = list(features)
        self._record(TenantActivated(tenant_id=self.id))

    def bump_perm_ver(self) -> int:
        self.perm_ver = int(self.perm_ver or 1) + 1
        return self.perm_ver

    @property
    def is_suspended(self) -> bool:
        return self.status == TenantStatus.SUSPENDED or not self.is_active
