from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.entities.invite import Invite
from src.domain.entities.membership import Membership
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.value_objects.phone import Phone
from src.schemas.auth import UserResponse


def user_to_response(
    user: User,
    *,
    tenant_id: str,
    tenant_name: str | None = None,
    role: UserRole,
    permissions: list[str] | None = None,
    perm_ver: int | None = None,
) -> UserResponse:
    phone = None
    if user.phone:
        from src.infrastructure.persistence.mongo.embeds import MobileInfo

        phone = MobileInfo(
            country_code=user.phone.country_code,
            phone_number=user.phone.phone_number,
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        phone=phone,
        role=role,
        is_outsourced=user.is_outsourced,
        is_active=user.is_active,
        created_at=user.created_at or datetime.now(),
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        permissions=permissions,
        perm_ver=perm_ver,
    )


@dataclass
class InviteResult:
    invite: Invite


@dataclass
class TenantResult:
    tenant: Tenant


@dataclass
class LoginResult:
    access_token: str
    expires_in_seconds: int
    user: UserResponse
    refresh_token: str | None = None
