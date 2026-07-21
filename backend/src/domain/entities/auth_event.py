from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.domain.utils import now_hk


@dataclass
class AuthEvent:
    id: str
    event_type: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    actor_user_id: Optional[str] = None
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    @classmethod
    def record(
        cls,
        *,
        event_id: str,
        event_type: str,
        tenant_id: str | None = None,
        user_id: str | None = None,
        actor_user_id: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> AuthEvent:
        return cls(
            id=event_id,
            event_type=event_type,
            tenant_id=tenant_id,
            user_id=user_id,
            actor_user_id=actor_user_id,
            detail=detail or {},
            created_at=now_hk(),
        )
