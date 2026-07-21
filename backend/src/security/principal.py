from __future__ import annotations

from dataclasses import dataclass, field

from src.models.enums import UserRole


@dataclass(slots=True)
class Principal:
    """Authenticated actor from JWT claims (no Identity DB lookup on Tracking)."""

    user_id: str
    tenant_id: str
    role: UserRole
    email: str
    full_name: str | None = None
    role_ids: list[str] = field(default_factory=list)
    perm_ver: int = 1
    scopes: list[str] = field(default_factory=list)
    # Resolved permissions (Identity path) or loaded from cache (Tracking)
    permissions: frozenset[str] = field(default_factory=frozenset)
    # Raw bearer for Identity permission fetch on Tracking
    bearer_token: str | None = None

    @property
    def id(self) -> str:
        return self.user_id

    def has_permission(self, code: str) -> bool:
        if code in self.permissions:
            return True
        if code in self.scopes:
            return True
        return False
