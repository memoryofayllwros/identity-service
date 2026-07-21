from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, EmailStr, Field

from src.application.dto import LoginResult, user_to_response
from src.application.services.auth_application_service import AuthApplicationService
from src.application.services.authorization_service import AuthorizationService
from src.application.services.membership_service import MembershipService
from src.domain.entities.tenant import Tenant
from src.domain.enums import UserRole
from src.domain.events import TenantCreated
from src.domain.repositories import AuthEventRepository, TenantRepository, UserRepository
from src.infrastructure.messaging.event_publisher import EventPublisher
from src.infrastructure.persistence.mongo._utils import new_id
from src.schemas.auth import UserResponse
from src.security.security import hash_password
from src.shared.permissions import PLAN_FEATURES


class TenantRegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=200)
    tenant_slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    plan: str = "starter"
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class TenantRegisterResponse(BaseModel):
    tenant_id: str
    slug: str
    access_token: str
    refresh_token: str
    expires_in_seconds: int
    user: UserResponse


@dataclass
class RegisterTenantHandler:
    tenant_repo: TenantRepository
    user_repo: UserRepository
    membership_service: MembershipService
    authz: AuthorizationService
    auth_events: AuthEventRepository
    publisher: EventPublisher
    auth_app: AuthApplicationService

    async def execute(self, payload: TenantRegisterRequest) -> TenantRegisterResponse:
        from fastapi import HTTPException, status
        from src.domain.entities.user import User

        if await self.tenant_repo.find_by_slug(payload.tenant_slug):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists.")
        if await self.user_repo.find_by_email(str(payload.email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")
        if await self.user_repo.find_by_username(payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

        await self.authz.ensure_platform_role_templates()
        plan = payload.plan if payload.plan in PLAN_FEATURES else "starter"
        features = list(PLAN_FEATURES.get(plan, PLAN_FEATURES["starter"]))
        tenant = Tenant(
            id=new_id(),
            name=payload.tenant_name,
            slug=payload.tenant_slug,
            plan=plan,
            status="active",
            features=features,
            is_active=True,
            perm_ver=1,
        )
        await self.tenant_repo.save(tenant)
        await self.authz.ensure_tenant_roles(tenant.id)

        user = User(
            id=new_id(),
            username=payload.username,
            email=str(payload.email),
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        await self.user_repo.save(user)
        membership = await self.membership_service.ensure_membership(
            tenant_id=tenant.id,
            user_id=user.id,
            role=UserRole.ADMIN,
        )
        await self.publisher.publish(
            TenantCreated(tenant_id=tenant.id, name=tenant.name, slug=tenant.slug)
        )
        from src.domain.entities.auth_event import AuthEvent

        await self.auth_events.save(
            AuthEvent.record(
                event_id=new_id(),
                event_type="tenant.registered",
                tenant_id=tenant.id,
                user_id=user.id,
                detail={"slug": tenant.slug, "plan": plan},
            )
        )
        login: LoginResult = await self.auth_app._issue_login(user, membership, tenant)
        return TenantRegisterResponse(
            tenant_id=tenant.id,
            slug=tenant.slug,
            access_token=login.access_token,
            refresh_token=login.refresh_token or "",
            expires_in_seconds=login.expires_in_seconds,
            user=login.user,
        )
