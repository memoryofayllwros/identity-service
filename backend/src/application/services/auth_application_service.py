from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import LoginResult, user_to_response
from src.application.services.authorization_service import AuthorizationService
from src.application.services.membership_service import MembershipService
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.entities.membership import Membership
from src.domain.repositories import AuthEventRepository, TenantRepository, UserRepository
from src.infrastructure.settings import get_settings
from src.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ProfileUpdate,
    RegisterRequest,
    UserResponse,
)
from src.security.security import (
    SecurityError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


def mobile_digits_from_pair(country_code: str, phone_number: str) -> str:
    cc = country_code.strip().lstrip("+")
    return f"{cc}{phone_number.strip()}"


@dataclass
class AuthApplicationService:
    user_repo: UserRepository
    tenant_repo: TenantRepository
    membership_service: MembershipService
    authz: AuthorizationService
    auth_events: AuthEventRepository
    default_tenant_id: str

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

    async def _active_membership(self, user: User) -> tuple[Membership, Tenant]:
        from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler

        tenant = await EnsureDefaultTenantHandler(
            self.tenant_repo, self.authz, self.membership_service._publisher
        ).execute()
        membership = await self.membership_service.membership_repo.find_active_by_user(user.id)
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
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is suspended.",
            )
        return membership, tenant_doc

    async def _issue_login(
        self,
        user: User,
        membership: Membership,
        tenant: Tenant,
    ) -> LoginResult:
        perms = await self.authz.permissions_for_membership(membership)
        perm_ver = await self.authz.membership_perm_ver(membership, tenant)
        settings = get_settings()
        token = create_access_token(
            user.id,
            user.email,
            membership.role.value,
            tenant_id=membership.tenant_id,
            role_ids=list(membership.role_ids),
            perm_ver=perm_ver,
            scopes=list(perms)[:32],
        )
        refresh = create_refresh_token(user.id, tenant_id=membership.tenant_id)
        return LoginResult(
            access_token=token,
            expires_in_seconds=settings.jwt_expire_minutes * 60,
            user=user_to_response(
                user,
                tenant_id=membership.tenant_id,
                tenant_name=tenant.name,
                role=membership.role,
                permissions=list(perms),
                perm_ver=perm_ver,
            ),
            refresh_token=refresh,
        )

    async def register(self, payload: RegisterRequest) -> UserResponse:
        from fastapi import HTTPException, status
        from src.domain.enums import UserRole
        from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler
        from src.infrastructure.persistence.mongo._utils import new_id

        if await self.user_repo.count() > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is closed. Contact an administrator.",
            )
        if await self.user_repo.find_by_username(payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
        if await self.user_repo.find_by_email(str(payload.email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

        tenant = await EnsureDefaultTenantHandler(
            self.tenant_repo, self.authz, self.membership_service._publisher
        ).execute()
        phone = None
        if payload.phone:
            from src.domain.value_objects.phone import Phone

            phone = Phone(
                country_code=payload.phone.country_code,
                phone_number=payload.phone.phone_number,
            )
        user = User(
            id=new_id(),
            username=payload.username,
            email=str(payload.email),
            full_name=payload.full_name,
            phone=phone,
            password_hash=hash_password(payload.password),
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
        from fastapi import HTTPException, status

        user = await self._find_by_login(payload.mobile)
        if user is None or not verify_password(payload.password, user.password_hash):
            await self._record_event("auth.login_failed", detail={"identifier": payload.mobile})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive.",
            )
        membership, tenant = await self._active_membership(user)
        result = await self._issue_login(user, membership, tenant)
        await self._record_event(
            "auth.login",
            tenant_id=membership.tenant_id,
            user_id=user.id,
        )
        return result

    async def refresh(self, refresh_token: str) -> LoginResult:
        from fastapi import HTTPException, status

        try:
            token_payload = decode_refresh_token(refresh_token)
        except SecurityError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            ) from exc
        user_id = token_payload.get("sub")
        tenant_id = token_payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload.",
            )
        user = await self.user_repo.find_by_id(user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive or missing.",
            )
        membership = await self.membership_service.membership_repo.find_by_tenant_and_user(
            tenant_id, user_id
        )
        if membership is None or not membership.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Membership inactive or missing.",
            )
        tenant = await self.tenant_repo.find_by_id(tenant_id)
        if tenant is None or tenant.is_suspended:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is suspended.",
            )
        return await self._issue_login(user, membership, tenant)

    async def me(self, user: User) -> UserResponse:
        membership, tenant = await self._active_membership(user)
        perms = await self.authz.permissions_for_membership(membership)
        return user_to_response(
            user,
            tenant_id=membership.tenant_id,
            tenant_name=tenant.name,
            role=membership.role,
            permissions=list(perms),
            perm_ver=await self.authz.membership_perm_ver(membership, tenant),
        )

    async def my_permissions(self, user: User) -> dict:
        membership, tenant = await self._active_membership(user)
        perms = await self.authz.permissions_for_membership(membership)
        return {
            "user_id": user.id,
            "tenant_id": membership.tenant_id,
            "role_ids": list(membership.role_ids),
            "perm_ver": await self.authz.membership_perm_ver(membership, tenant),
            "permissions": list(perms),
        }

    async def update_profile(self, user: User, payload: ProfileUpdate) -> UserResponse:
        from fastapi import HTTPException, status
        from src.domain.value_objects.phone import Phone

        updates = payload.model_dump(exclude_unset=True)
        email = updates.get("email")
        if email is not None:
            existing = await self.user_repo.find_by_email(str(email))
            if existing and existing.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")
        phone = None
        if "phone" in updates and updates["phone"] is not None:
            phone = Phone(
                country_code=updates["phone"].country_code,
                phone_number=updates["phone"].phone_number,
            )
        user.update_profile(
            email=str(email) if email else None,
            full_name=updates.get("full_name"),
            phone=phone if "phone" in updates else None,
        )
        await self.user_repo.save(user)
        refreshed = await self.user_repo.find_by_id(user.id)
        return await self.me(refreshed or user)

    async def list_users(self) -> list[UserResponse]:
        from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler

        tenant = await EnsureDefaultTenantHandler(
            self.tenant_repo, self.authz, self.membership_service._publisher
        ).execute()
        users = await self.user_repo.find_all()
        results: list[UserResponse] = []
        for user in users:
            membership = await self.membership_service.membership_repo.find_by_tenant_and_user(
                tenant.id, user.id
            )
            role = membership.role if membership else UserRole.OPERATIONS
            results.append(
                user_to_response(user, tenant_id=tenant.id, tenant_name=tenant.name, role=role)
            )
        return results

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
        from src.domain.entities.auth_event import AuthEvent
        from src.infrastructure.persistence.mongo._utils import new_id

        await self.auth_events.save(
            AuthEvent.record(event_id=new_id(), event_type=event_type, **kwargs)
        )


from src.domain.enums import UserRole  # noqa: E402
