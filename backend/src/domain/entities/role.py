from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Role:
    id: str
    code: str
    name: str
    permissions: list[str] = field(default_factory=list)
    tenant_id: Optional[str] = None
    is_system: bool = True
    created_at: Optional[datetime] = None

    def grant_permission(self, code: str) -> None:
        if code not in self.permissions:
            self.permissions.append(code)

    def revoke_permission(self, code: str) -> None:
        if code in self.permissions:
            self.permissions.remove(code)
