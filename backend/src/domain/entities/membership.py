from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.entities._base import AggregateRoot
from src.domain.enums import UserRole


@dataclass
class Membership(AggregateRoot):
    id: str
    tenant_id: str
    user_id: str
    role: UserRole
    role_ids: list[str] = field(default_factory=list)
    perm_ver: int = 1
    is_active: bool = True
    created_at: Optional[datetime] = None

    def assign_roles(self, role_ids: list[str], role: UserRole | None = None) -> None:
        if not self.is_active:
            raise ValueError("Cannot assign roles to inactive membership.")
        self.role_ids = list(role_ids)
        if role is not None:
            self.role = role

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self, role: UserRole | None = None) -> None:
        self.is_active = True
        if role is not None:
            self.role = role

    def sync_perm_ver(self, perm_ver: int) -> None:
        self.perm_ver = perm_ver
