"""Auth / RBAC audit events (Identity)."""

from typing import Any, Optional

from beanie import Document, Indexed
from pydantic import Field

from src.models._utils import HongKongDatetime, as_hk, new_id


class AuthEventDoc(Document):
    event_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    event_type: Indexed(str)
    tenant_id: Optional[Indexed(str)] = None
    user_id: Optional[Indexed(str)] = None
    actor_user_id: Optional[str] = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "auth_events"
        indexes = [
            [("tenant_id", 1), ("created_at", -1)],
            [("event_type", 1), ("created_at", -1)],
        ]
