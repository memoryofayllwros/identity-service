"""Tenant invite (self-serve membership)."""

from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from src.models._utils import HongKongDatetime, as_hk, new_id


class InviteDoc(Document):
    invite_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    tenant_id: Indexed(str)
    email: Indexed(str)
    role_code: str = "operations"
    token: Indexed(str, unique=True) = Field(default_factory=new_id)
    status: str = "pending"  # pending | accepted | revoked | expired
    invited_by_user_id: Optional[str] = None
    expires_at: HongKongDatetime
    accepted_at: Optional[HongKongDatetime] = None
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "invites"
        indexes = [
            [("tenant_id", 1), ("email", 1)],
            ("status",),
        ]
