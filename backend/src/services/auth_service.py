from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from src.infrastructure.settings import get_settings
from src.models.membership_doc import MembershipDoc
from src.models.tenant_doc import TenantDoc
from src.models.user_doc import UserDoc
from src.models.enums import UserRole
from src.models._utils import new_id
from src.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    ProfileUpdate,
    RegisterRequest,
    UserResponse,
    mobile_digits_from_pair,
)
from src.security.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
    SecurityError,
)
from src.services.audit_service import record_auth_event
from src.services.base import get_identity_or_404
from src.services.rbac_service import (
    bump_tenant_perm_ver,
    ensure_platform_role_templates,
    ensure_tenant_roles,
    membership_perm_ver,
    permissions_for_membership,
    resolve_role_ids_for_legacy,
)
from src.shared.constants import DEFAULT_TENANT_NAME, DEFAULT_TENANT_SLUG
from src.shared.events import TenantCreated, UserAddedToTenant, dispatcher
from src.shared.permissions import PLAN_FEATURES


async def ensure_default_tenant() -> TenantDoc:
    settings = get_settings()
    tenant_id = settings.tenant_instance_id
    tenant = await TenantDoc.find_one(TenantDoc.tenant_id == tenant_id)
    if tenant is not None:
        if tenant.tenant_id != tenant_id:
            raise RuntimeError("Configured TENANT_INSTANCE_ID does not match tenant record.")
        await ensure_tenant_roles(tenant.tenant_id)
        return tenant
    await ensure_platform_role_templates()
    features = list(PLAN_FEATURES.get("enterprise", []))
    slug = tenant_id
    tenant = TenantDoc(
        tenant_id=tenant_id,
        name=DEFAULT_TENANT_NAME,
        slug=slug or DEFAULT_TENANT_SLUG,
        plan="enterprise",
        status="active",
        features=features,
        is_active=True,
        perm_ver=1,
    )
    await tenant.insert()
    await ensure_tenant_roles(tenant.tenant_id)
    await dispatcher.publish(
        TenantCreated(
            tenant_id=tenant.tenant_id,
            name=tenant.name,
            slug=tenant.slug,
        )
    )
    return tenant


async def ensure_membership(
    *,
    tenant_id: str,
    user_id: str,
    role: UserRole,
) -> MembershipDoc:
    await ensure_tenant_roles(tenant_id)
    role_ids = await resolve_role_ids_for_legacy(role, tenant_id)
    tenant = await TenantDoc.find_one(TenantDoc.tenant_id == tenant_id)
    perm_ver = int(tenant.perm_ver or 1) if tenant else 1

    existing = await MembershipDoc.find_one(
        MembershipDoc.tenant_id == tenant_id,
        MembershipDoc.user_id == user_id,
    )
    if existing is not None:
        updates: dict = {}
        if existing.role != role or not existing.is_active:
            updates["role"] = role
            updates["is_active"] = True
        if list(existing.role_ids) != role_ids:
            updates["role_ids"] = role_ids
        if existing.perm_ver != perm_ver:
            updates["perm_ver"] = perm_ver
        if updates:
            await existing.set(updates)
            await bump_tenant_perm_ver(tenant_id)
            refreshed = await MembershipDoc.find_one(
                MembershipDoc.membership_id == existing.membership_id
            )
            return refreshed or existing
        return existing
    membership = MembershipDoc(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        role_ids=role_ids,
        perm_ver=perm_ver,
    )
    await membership.insert()
    await dispatcher.publish(
        UserAddedToTenant(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role.value,
        )
    )
    return membership


def user_to_response(
    user: UserDoc,
    *,
    tenant_id: str,
    tenant_name: str | None = None,
    permissions: list[str] | None = None,
    perm_ver: int | None = None,
) -> UserResponse:
    return UserResponse(
        id=user.user_id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_outsourced=user.is_outsourced,
        is_active=user.is_active,
        created_at=user.created_at,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        permissions=permissions,
        perm_ver=perm_ver,
    )


class AuthService:
    async def _find_by_login(self, identifier: str) -> UserDoc | None:
        user = await UserDoc.find_one(UserDoc.username == identifier)
        if user:
            return user
        user = await UserDoc.find_one(UserDoc.email == identifier)
        if user:
            return user
        users = await UserDoc.find_all().to_list()
        for candidate in users:
            if candidate.phone:
                digits = mobile_digits_from_pair(
                    candidate.phone.country_code,
                    candidate.phone.phone_number,
                )
                if digits == identifier:
                    return candidate
        return None

    async def _active_membership(self, user: UserDoc) -> tuple[MembershipDoc, TenantDoc]:
        tenant = await ensure_default_tenant()
        membership = await MembershipDoc.find_one(
            MembershipDoc.user_id == user.user_id,
            MembershipDoc.is_active == True,  # noqa: E712
        )
        if membership is None:
            membership = await ensure_membership(
                tenant_id=tenant.tenant_id,
                user_id=user.user_id,
                role=user.role,
            )
        tenant_doc = await TenantDoc.find_one(TenantDoc.tenant_id == membership.tenant_id)
        if tenant_doc is None:
            tenant_doc = tenant
        if tenant_doc.status == "suspended" or not tenant_doc.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is suspended.",
            )
        return membership, tenant_doc

    async def _issue_login(
        self,
        user: UserDoc,
        membership: MembershipDoc,
        tenant: TenantDoc,
    ) -> LoginResponse:
        if not membership.role_ids:
            role_ids = await resolve_role_ids_for_legacy(membership.role, membership.tenant_id)
            await membership.set({"role_ids": role_ids})
            membership.role_ids = role_ids
        perms = await permissions_for_membership(membership)
        perm_ver = await membership_perm_ver(membership, tenant)
        settings = get_settings()
        token = create_access_token(
            user.user_id,
            user.email,
            membership.role.value,
            tenant_id=membership.tenant_id,
            role_ids=list(membership.role_ids),
            perm_ver=perm_ver,
            scopes=list(perms)[:32],
        )
        refresh = create_refresh_token(user.user_id, tenant_id=membership.tenant_id)
        user.role = membership.role
        return LoginResponse(
            access_token=token,
            expires_in_seconds=settings.jwt_expire_minutes * 60,
            user=user_to_response(
                user,
                tenant_id=membership.tenant_id,
                tenant_name=tenant.name,
                permissions=list(perms),
                perm_ver=perm_ver,
            ),
            refresh_token=refresh,
        )

    async def register(self, payload: RegisterRequest) -> UserResponse:
        user_count = await UserDoc.find_all().count()
        if user_count > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration is closed. Contact an administrator.",
            )

        if await UserDoc.find_one(UserDoc.username == payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
        if await UserDoc.find_one(UserDoc.email == payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

        tenant = await ensure_default_tenant()
        user = UserDoc(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            phone=payload.phone,
            password_hash=hash_password(payload.password),
            role=UserRole.ADMIN,
            is_outsourced=payload.is_outsourced,
        )
        await user.insert()
        membership = await ensure_membership(
            tenant_id=tenant.tenant_id,
            user_id=user.user_id,
            role=UserRole.ADMIN,
        )
        await record_auth_event(
            "user.registered",
            tenant_id=tenant.tenant_id,
            user_id=user.user_id,
        )
        perms = await permissions_for_membership(membership)
        return user_to_response(
            user,
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.name,
            permissions=list(perms),
            perm_ver=membership.perm_ver,
        )

    async def login(self, payload: LoginRequest) -> LoginResponse:
        user = await self._find_by_login(payload.mobile)
        if user is None or not verify_password(payload.password, user.password_hash):
            await record_auth_event("auth.login_failed", detail={"identifier": payload.mobile})
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
        await record_auth_event(
            "auth.login",
            tenant_id=membership.tenant_id,
            user_id=user.user_id,
        )
        return result

    async def refresh(self, refresh_token: str) -> LoginResponse:
        try:
            payload = decode_refresh_token(refresh_token)
        except SecurityError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            ) from exc
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload.",
            )
        user = await UserDoc.find_one(UserDoc.user_id == user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is inactive or missing.",
            )
        membership = await MembershipDoc.find_one(
            MembershipDoc.tenant_id == tenant_id,
            MembershipDoc.user_id == user_id,
            MembershipDoc.is_active == True,  # noqa: E712
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Membership inactive or missing.",
            )
        tenant = await TenantDoc.find_one(TenantDoc.tenant_id == tenant_id)
        if tenant is None or tenant.status == "suspended" or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is suspended.",
            )
        return await self._issue_login(user, membership, tenant)

    async def me(self, user: UserDoc) -> UserResponse:
        membership, tenant = await self._active_membership(user)
        user.role = membership.role
        perms = await permissions_for_membership(membership)
        return user_to_response(
            user,
            tenant_id=membership.tenant_id,
            tenant_name=tenant.name,
            permissions=list(perms),
            perm_ver=await membership_perm_ver(membership, tenant),
        )

    async def my_permissions(self, user: UserDoc) -> dict:
        membership, tenant = await self._active_membership(user)
        perms = await permissions_for_membership(membership)
        return {
            "user_id": user.user_id,
            "tenant_id": membership.tenant_id,
            "role_ids": list(membership.role_ids),
            "perm_ver": await membership_perm_ver(membership, tenant),
            "permissions": list(perms),
        }

    async def update_profile(self, user: UserDoc, payload: ProfileUpdate) -> UserResponse:
        updates = payload.model_dump(exclude_unset=True)
        if "email" in updates:
            existing = await UserDoc.find_one(UserDoc.email == updates["email"])
            if existing and existing.user_id != user.user_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")
        if updates:
            await user.set(updates)
        refreshed = await get_identity_or_404(UserDoc, "user_id", user.user_id)
        return await self.me(refreshed)

    async def list_users(self) -> list[UserResponse]:
        tenant = await ensure_default_tenant()
        users = await UserDoc.find_all().to_list()
        return [
            user_to_response(u, tenant_id=tenant.tenant_id, tenant_name=tenant.name)
            for u in users
        ]

    async def request_password_reset(self, payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
        return ForgotPasswordResponse(
            message=(
                "If an account exists for that identifier, your administrator can reset "
                "your password. Please contact your system administrator."
            ),
        )


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


async def register_tenant(payload: TenantRegisterRequest) -> TenantRegisterResponse:
    """Self-serve tenant signup — Identity only; Tracking never creates TenantDoc."""
    if await TenantDoc.find_one(TenantDoc.slug == payload.tenant_slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists.")
    if await UserDoc.find_one(UserDoc.email == payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")
    if await UserDoc.find_one(UserDoc.username == payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    await ensure_platform_role_templates()
    plan = payload.plan if payload.plan in PLAN_FEATURES else "starter"
    features = list(PLAN_FEATURES.get(plan, PLAN_FEATURES["starter"]))
    tenant = TenantDoc(
        tenant_id=new_id(),
        name=payload.tenant_name,
        slug=payload.tenant_slug,
        plan=plan,
        status="active",
        features=features,
        is_active=True,
        perm_ver=1,
    )
    await tenant.insert()
    await ensure_tenant_roles(tenant.tenant_id)

    user = UserDoc(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
    )
    await user.insert()
    membership = await ensure_membership(
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        role=UserRole.ADMIN,
    )
    await dispatcher.publish(
        TenantCreated(tenant_id=tenant.tenant_id, name=tenant.name, slug=tenant.slug)
    )
    await record_auth_event(
        "tenant.registered",
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        detail={"slug": tenant.slug, "plan": plan},
    )
    login = await AuthService()._issue_login(user, membership, tenant)
    return TenantRegisterResponse(
        tenant_id=tenant.tenant_id,
        slug=tenant.slug,
        access_token=login.access_token,
        refresh_token=login.refresh_token or "",
        expires_in_seconds=login.expires_in_seconds,
        user=login.user,
    )
