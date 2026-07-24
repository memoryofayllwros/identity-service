from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from src.infrastructure.persistence.mongo._utils import HongKongDatetime, as_hk, new_id
from src.infrastructure.persistence.mongo.embeds import MobileInfo


class UserDocument(Document):
    user_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    username: Indexed(str, unique=True)
    email: Indexed(str, unique=True)
    full_name: str
    phone: Optional[MobileInfo] = None
    position: str = ""
    password_hash: str
    must_change_password: bool = False
    is_outsourced: bool = False
    permissions: list[str] = Field(default_factory=list)
    status: str = "active"
    failed_login_count: int = 0
    lockout_until: Optional[HongKongDatetime] = None
    last_login_at: Optional[HongKongDatetime] = None
    created_at: HongKongDatetime = Field(default_factory=as_hk)
    updated_at: Optional[HongKongDatetime] = None

    class Settings:
        name = "users"
        indexes = [("status",)]


class TenantDocument(Document):
    """Single company profile for this deployment (not multi-tenant)."""

    tenant_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    name: str
    slug: Indexed(str, unique=True)
    status: str = "active"
    features: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)
    updated_at: Optional[HongKongDatetime] = None
    suspended_at: Optional[HongKongDatetime] = None

    class Settings:
        name = "tenants"
        indexes = [("is_active",), ("status",)]


class RoleDocument(Document):
    role_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    code: Indexed(str, unique=True)
    name: str
    permissions: list[str] = Field(default_factory=list)
    is_system: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)
    updated_at: Optional[HongKongDatetime] = None

    class Settings:
        name = "roles"
        indexes = [("is_system",)]


class AuthEventDocument(Document):
    event_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    event_type: Indexed(str)
    user_id: Optional[Indexed(str)] = None
    actor_user_id: Optional[str] = None
    detail: dict = Field(default_factory=dict)
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "auth_events"
        indexes = [
            [("event_type", 1), ("created_at", -1)],
        ]


class OutboxDocument(Document):
    record_id: Indexed(str, unique=True)
    event_type: str
    payload: dict = Field(default_factory=dict)
    published: bool = False
    created_at: HongKongDatetime = Field(default_factory=as_hk)
    published_at: Optional[HongKongDatetime] = None

    class Settings:
        name = "outbox"
        indexes = [
            [("published", 1), ("created_at", 1)],
        ]


IDENTITY_DOCUMENT_MODELS = [
    TenantDocument,
    UserDocument,
    RoleDocument,
    AuthEventDocument,
    OutboxDocument,
]
