from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.exceptions import TenantAlreadySuspended, TenantNotSuspended
from src.domain.utils import now_hk


@dataclass
class Tenant:
    id: str
    name: str
    slug: str
    plan: str = "enterprise"
    status: str = "active"
    features: list[str] = field(default_factory=list)
    is_active: bool = True
    perm_ver: int = 1
    created_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None

    def suspend(self) -> None:
        if self.status == "suspended":
            raise TenantAlreadySuspended()
        self.status = "suspended"
        self.is_active = False
        self.suspended_at = now_hk()

    def activate(self, features: list[str] | None = None) -> None:
        if self.status == "active" and self.is_active:
            return
        self.status = "active"
        self.is_active = True
        self.suspended_at = None
        if features is not None:
            self.features = list(features)

    def bump_perm_ver(self) -> int:
        self.perm_ver = int(self.perm_ver or 1) + 1
        return self.perm_ver

    @property
    def is_suspended(self) -> bool:
        return self.status == "suspended" or not self.is_active
