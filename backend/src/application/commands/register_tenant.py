from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, EmailStr, Field

from src.application.dto import LoginResult, UserDTO
from src.application.services.authorization_service import AuthorizationService
from src.application.services.membership_service import MembershipService
from src.application.services.token_issuance_service import TokenIssuanceService
from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.tenant import Tenant
from src.domain.enums import UserRole
from src.domain.exceptions import DuplicateEmail, DuplicateTenantSlug, DuplicateUsername
from src.domain.repositories import AuthEventRepository, TenantRepository, UserRepository
from src.domain.id_generator import IDGenerator
from src.application.ports.password_hasher import PasswordHasher
from src.domain.unit_of_work import UnitOfWork
from src.domain.value_objects.email import Email


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
    user: UserDTO


@dataclass
class RegisterTenantHandler:
    tenant_repo: TenantRepository
    user_repo: UserRepository
    membership_service: MembershipService
    authz: AuthorizationService
    auth_events: AuthEventRepository
    token_issuance: TokenIssuanceService
    uow: UnitOfWork
    id_gen: IDGenerator
    password_hasher: PasswordHasher

    async def execute(self, payload: TenantRegisterRequest) -> TenantRegisterResponse:
        from src.domain.entities.user import User

        if await self.tenant_repo.find_by_slug(payload.tenant_slug):
            raise DuplicateTenantSlug()
        if await self.user_repo.find_by_email(str(payload.email)):
            raise DuplicateEmail()
        if await self.user_repo.find_by_username(payload.username):
            raise DuplicateUsername()

        await self.authz.ensure_platform_role_templates()
        plan = self.authz.resolve_plan(payload.plan)
        features = self.authz.plan_features(plan)
        tenant = Tenant.create(
            tenant_id=self.id_gen(),
            name=payload.tenant_name,
            slug=payload.tenant_slug,
            plan=plan,
            features=features,
            perm_ver=1,
        )
        await self.authz.ensure_tenant_roles(tenant.id)

        user = User.register(
            user_id=self.id_gen(),
            username=payload.username,
            email=Email(str(payload.email)),
            full_name=payload.full_name,
            password_hash=self.password_hasher.hash(payload.password),
            tenant_id=tenant.id,
        )

        async with self.uow:
            self.uow.register(tenant)
            self.uow.register(user)
            membership = await self.membership_service.ensure_membership(
                tenant_id=tenant.id,
                user_id=user.id,
                role=UserRole.ADMIN,
                uow=self.uow,
            )
            await self.uow.commit()

        await self.auth_events.save(
            AuthEvent.record(
                event_id=self.id_gen(),
                event_type="tenant.registered",
                tenant_id=tenant.id,
                user_id=user.id,
                detail={"slug": tenant.slug, "plan": plan},
            )
        )
        login: LoginResult = await self.token_issuance.issue_login(user, membership, tenant)
        return TenantRegisterResponse(
            tenant_id=tenant.id,
            slug=tenant.slug,
            access_token=login.access_token,
            refresh_token=login.refresh_token or "",
            expires_in_seconds=login.expires_in_seconds,
            user=login.user,
        )
