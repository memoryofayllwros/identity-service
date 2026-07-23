from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from src.domain.entities._base import AggregateRoot
from src.domain.enums import InviteStatus
from src.domain.events import InviteAccepted, InviteCreated, InviteRevoked
from src.domain.exceptions import InviteExpired, InviteNotPending
from src.domain.utils import now_hk
from src.domain.value_objects.email import Email


@dataclass
class Invite(AggregateRoot):
    id: str
    tenant_id: str
    email: Email
    token: str
    expires_at: datetime
    role_code: str = "operations"
    status: InviteStatus = InviteStatus.PENDING
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
        invite = cls(
            id=invite_id,
            tenant_id=tenant_id,
            email=Email(email),
            token=token,
            role_code=role_code,
            status=InviteStatus.PENDING,
            invited_by_user_id=invited_by_user_id,
            expires_at=now_hk() + timedelta(days=expires_in_days),
            created_at=now_hk(),
        )
        invite._record(
            InviteCreated(
                invite_id=invite.id,
                tenant_id=invite.tenant_id,
                email=str(invite.email),
            )
        )
        return invite

    def accept(self, *, user_id: str) -> None:
        if self.status != InviteStatus.PENDING:
            raise InviteNotPending()
        if self.is_expired:
            self.status = InviteStatus.EXPIRED
            raise InviteExpired()
        self.status = InviteStatus.ACCEPTED
        self.accepted_at = now_hk()
        self._record(
            InviteAccepted(
                invite_id=self.id,
                tenant_id=self.tenant_id,
                user_id=user_id,
            )
        )

    def revoke(self) -> None:
        self.status = InviteStatus.REVOKED
        self._record(InviteRevoked(invite_id=self.id, tenant_id=self.tenant_id))

    def expire(self) -> None:
        self.status = InviteStatus.EXPIRED

    @property
    def is_expired(self) -> bool:
        return self.expires_at < now_hk()

    @property
    def is_pending(self) -> bool:
        return self.status == InviteStatus.PENDING
