from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from src.domain.exceptions import InviteExpired, InviteNotPending
from src.domain.utils import now_hk


@dataclass
class Invite:
    id: str
    tenant_id: str
    email: str
    token: str
    expires_at: datetime
    role_code: str = "operations"
    status: str = "pending"
    invited_by_user_id: Optional[str] = None
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        *,
        invite_id: str,
        tenant_id: str,
        email: str,
        token: str,
        role_code: str,
        invited_by_user_id: str | None,
        expires_in_days: int = 7,
    ) -> Invite:
        return cls(
            id=invite_id,
            tenant_id=tenant_id,
            email=email.lower(),
            token=token,
            role_code=role_code,
            status="pending",
            invited_by_user_id=invited_by_user_id,
            expires_at=now_hk() + timedelta(days=expires_in_days),
            created_at=now_hk(),
        )

    def accept(self) -> None:
        if self.status != "pending":
            raise InviteNotPending()
        if self.is_expired:
            self.status = "expired"
            raise InviteExpired()
        self.status = "accepted"
        self.accepted_at = now_hk()

    def revoke(self) -> None:
        self.status = "revoked"

    def expire(self) -> None:
        self.status = "expired"

    @property
    def is_expired(self) -> bool:
        return self.expires_at < now_hk()

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"
