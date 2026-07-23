from __future__ import annotations

from dataclasses import dataclass

from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler
from src.application.dto import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResult,
    ProfileUpdate,
    RegisterRequest,
    UserResponse,
    user_to_response,
)
from src.application.ports.password_hasher import PasswordHasher
from src.application.ports.token_service import TokenService
from src.application.queries.user_queries import GetUserHandler, GetUserQuery
from src.application.services.authorization_service import AuthorizationService
from src.application.services.membership_service import MembershipService
from src.application.services.token_issuance_service import TokenIssuanceService
from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.membership import Membership
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.exceptions import (
    DuplicateEmail,
    DuplicateUsername,
    InvalidCredentials,
    InvalidToken,
    MembershipInactive,
    RegistrationClosed,
    TenantSuspended,
    UserInactive,
)
from src.domain.id_generator import IDGenerator
from src.domain.repositories import AuthEventRepository, TenantRepository, UserRepository
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone


@dataclass
class AuthApplicationService:
    user_repo: UserRepository
    tenant_repo: TenantRepository
    membership_service: MembershipService
    authz: AuthorizationService
    auth_events: AuthEventRepository
    default_tenant_id: str
    jwt_expire_minutes: int
    id_gen: IDGenerator
    password_hasher: PasswordHasher
    token_service: TokenService
    token_issuance: TokenIssuanceService
    get_user_handler: GetUserHandler
    ensure_default_tenant_handler: EnsureDefaultTenantHandler

    async def _find_by_login(self, identifier: str) -> User | None:
        user = await self.user_repo.find_by_username(identifier)
        if user:
            return user
        user = await self.user_repo.find_by_email(identifier)
        if user:
            return user
        for candidate in await self.user_repo.find_all():
            if candidate.phone and candidate.phone.digits() == identifier:
                return candidate
        return None

    async def _ensure_default_tenant(self) -> Tenant:
        return await self.ensure_default_tenant_handler.execute()

    async def _active_membership(self, user: User) -> tuple[Membership, Tenant]:
        tenant = await self._ensure_default_tenant()
        membership = await self.membership_service.find_active_for_user(user.id)
        if membership is None:
            membership = await self.membership_service.ensure_membership(
                tenant_id=tenant.id,
                user_id=user.id,
                role=UserRole.OPERATIONS,
            )
        tenant_doc = await self.tenant_repo.find_by_id(membership.tenant_id)
        if tenant_doc is None:
            tenant_doc = tenant
        if tenant_doc.is_suspended:
            raise TenantSuspended()
        return membership, tenant_doc

    async def issue_login(
        self,
        user: User,
        membership: Membership,
        tenant: Tenant,
    ) -> LoginResult:
        return await self.token_issuance.issue_login(user, membership, tenant)

    async def register(self, payload: RegisterRequest) -> UserResponse:
        if await self.user_repo.count() > 0:
            raise RegistrationClosed()
        if await self.user_repo.find_by_username(payload.username):
            raise DuplicateUsername()
        if await self.user_repo.find_by_email(str(payload.email)):
            raise DuplicateEmail()

        tenant = await self._ensure_default_tenant()
        phone = None
        if payload.phone:
            phone = Phone(
                country_code=payload.phone.country_code,
                phone_number=payload.phone.phone_number,
            )
        user = User(
            id=self.id_gen(),
            username=payload.username,
            email=Email(str(payload.email)),
            full_name=payload.full_name,
            phone=phone,
            password_hash=self.password_hasher.hash(payload.password),
            is_outsourced=payload.is_outsourced,
        )
        await self.user_repo.save(user)
        membership = await self.membership_service.ensure_membership(
            tenant_id=tenant.id,
            user_id=user.id,
            role=UserRole.ADMIN,
        )
        await self._record_event("user.registered", tenant_id=tenant.id, user_id=user.id)
        perms = await self.authz.permissions_for_membership(membership)
        return user_to_response(
            user,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            role=membership.role,
            permissions=list(perms),
            perm_ver=membership.perm_ver,
        )

    async def login(self, payload: LoginRequest) -> LoginResult:
        user = await self._find_by_login(payload.mobile)
        if user is None or not self.password_hasher.verify(payload.password, user.password_hash):
            await self._record_event("auth.login_failed", detail={"identifier": payload.mobile})
            raise InvalidCredentials()
        if not user.is_active:
            raise UserInactive()
        membership, tenant = await self._active_membership(user)
        result = await self.issue_login(user, membership, tenant)
        await self._record_event(
            "auth.login",
            tenant_id=membership.tenant_id,
            user_id=user.id,
        )
        return result

    async def refresh(self, refresh_token: str) -> LoginResult:
        token_payload = self.token_service.decode_refresh_token(refresh_token)
        user_id = token_payload.get("sub")
        tenant_id = token_payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise InvalidToken("Invalid refresh token payload.")
        user = await self.user_repo.find_by_id(user_id)
        if user is None or not user.is_active:
            raise UserInactive("User is inactive or missing.")
        membership = await self.membership_service.find_for_tenant_and_user(
            tenant_id, user_id
        )
        if membership is None or not membership.is_active:
            raise MembershipInactive()
        tenant = await self.tenant_repo.find_by_id(tenant_id)
        if tenant is None or tenant.is_suspended:
            raise TenantSuspended()
        return await self.issue_login(user, membership, tenant)

    async def update_profile(self, user: User, payload: ProfileUpdate) -> UserResponse:
        updates = payload.model_dump(exclude_unset=True)
        email = updates.get("email")
        if email is not None:
            existing = await self.user_repo.find_by_email(str(email))
            if existing and existing.id != user.id:
                raise DuplicateEmail()
        phone = None
        if "phone" in updates and updates["phone"] is not None:
            phone = Phone(
                country_code=updates["phone"].country_code,
                phone_number=updates["phone"].phone_number,
            )
        user.update_profile(
            email=Email(str(email)) if email else None,
            full_name=updates.get("full_name"),
            phone=phone if "phone" in updates else None,
        )
        await self.user_repo.save(user)
        refreshed = await self.user_repo.find_by_id(user.id)
        return await self.get_user_handler.execute(
            GetUserQuery(user_id=user.id, user=refreshed or user)
        )

    async def request_password_reset(
        self, payload: ForgotPasswordRequest
    ) -> ForgotPasswordResponse:
        return ForgotPasswordResponse(
            message=(
                "If an account exists for that identifier, your administrator can reset "
                "your password. Please contact your system administrator."
            ),
        )

    async def _record_event(self, event_type: str, **kwargs) -> None:
        await self.auth_events.save(
            AuthEvent.record(event_id=self.id_gen(), event_type=event_type, **kwargs)
        )
