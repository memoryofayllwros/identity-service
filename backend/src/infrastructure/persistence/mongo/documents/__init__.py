from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from src.domain.enums import UserRole
from src.infrastructure.persistence.mongo._utils import HongKongDatetime, as_hk, new_id
from src.infrastructure.persistence.mongo.embeds import MobileInfo


class UserDocument(Document):
    user_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    username: Indexed(str, unique=True)
    email: Indexed(str, unique=True)
    full_name: str
    phone: Optional[MobileInfo] = None
    password_hash: str
    is_outsourced: bool = False
    is_active: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "users"


class TenantDocument(Document):
    tenant_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    name: str
    slug: Indexed(str, unique=True)
    plan: str = "enterprise"
    status: str = "active"
    features: list[str] = Field(default_factory=list)
    is_active: bool = True
    perm_ver: int = 1
    created_at: HongKongDatetime = Field(default_factory=as_hk)
    suspended_at: Optional[HongKongDatetime] = None

    class Settings:
        name = "tenants"
        indexes = [("is_active",), ("status",), ("plan",)]


class MembershipDocument(Document):
    membership_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    tenant_id: Indexed(str)
    user_id: Indexed(str)
    role: UserRole
    role_ids: list[str] = Field(default_factory=list)
    perm_ver: int = 1
    is_active: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "memberships"
        indexes = [
            [("tenant_id", 1), ("user_id", 1)],
            ("role",),
            ("is_active",),
        ]


class RoleDocument(Document):
    role_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    tenant_id: Optional[Indexed(str)] = None
    code: Indexed(str)
    name: str
    permissions: list[str] = Field(default_factory=list)
    is_system: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "roles"
        indexes = [
            [("tenant_id", 1), ("code", 1)],
            ("is_system",),
        ]


class PermissionDocument(Document):
    permission_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    code: Indexed(str, unique=True)
    description: str = ""
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "permissions"


class InviteDocument(Document):
    invite_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    tenant_id: Indexed(str)
    email: Indexed(str)
    role_code: str = "operations"
    token: Indexed(str, unique=True) = Field(default_factory=new_id)
    status: str = "pending"
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


class AuthEventDocument(Document):
    event_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    event_type: Indexed(str)
    tenant_id: Optional[Indexed(str)] = None
    user_id: Optional[Indexed(str)] = None
    actor_user_id: Optional[str] = None
    detail: dict = Field(default_factory=dict)
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "auth_events"
        indexes = [
            [("tenant_id", 1), ("created_at", -1)],
            [("event_type", 1), ("created_at", -1)],
        ]


IDENTITY_DOCUMENT_MODELS = [
    TenantDocument,
    MembershipDocument,
    UserDocument,
    RoleDocument,
    PermissionDocument,
    InviteDocument,
    AuthEventDocument,
]
