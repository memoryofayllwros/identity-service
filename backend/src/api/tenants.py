"""Identity tenant lifecycle: directory, invites, entitlements, suspend (single-tenant Phase 1)."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.application.commands.accept_invite import AcceptInviteCommand
from src.application.commands.invite_user import InviteUserCommand
from src.application.commands.suspend_tenant import ActivateTenantCommand, SuspendTenantCommand
from src.domain.enums import TenantStatus, UserRole
from src.infrastructure.dependencies import (
    ensure_default_tenant,
    get_accept_invite_handler,
    get_activate_tenant_handler,
    get_invite_repository,
    get_invite_user_handler,
    get_suspend_tenant_handler,
    get_tenant_repository,
)
from src.infrastructure.security.dependencies import get_current_principal, require_permission, require_roles
from src.infrastructure.security.principal import Principal
from src.shared.permissions import (
    IDENTITY_INVITE_MANAGE,
    IDENTITY_TENANT_ADMIN,
    IDENTITY_USER_ADMIN,
    PLAN_FEATURES,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])
AdminDep = Annotated[Principal, Depends(require_roles(UserRole.ADMIN))]
TenantAdminDep = Annotated[
    Principal,
    Depends(require_permission(IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN)),
]
InviteDep = Annotated[
    Principal,
    Depends(require_permission(IDENTITY_INVITE_MANAGE, IDENTITY_TENANT_ADMIN)),
]


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    slug: str
    plan: str
    status: str = "active"
    features: list[str] = Field(default_factory=list)
    is_active: bool
    perm_ver: int = 1

    model_config = ConfigDict(from_attributes=True)


class EntitlementsResponse(BaseModel):
    tenant_id: str
    plan: str
    status: str
    features: list[str]
    is_active: bool


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role_code: str = "operations"


class InviteResponse(BaseModel):
    invite_id: str
    tenant_id: str
    email: EmailStr
    role_code: str
    token: str
    status: str
    expires_at: object

    model_config = ConfigDict(from_attributes=True)


class InviteAcceptRequest(BaseModel):
    token: str = Field(min_length=8)
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class SuspendRequest(BaseModel):
    reason: Optional[str] = None


def _tenant_response(tenant) -> TenantResponse:
    return TenantResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        status=tenant.status,
        features=list(tenant.features),
        is_active=tenant.is_active,
        perm_ver=tenant.perm_ver,
    )


def _invite_response(invite) -> InviteResponse:
    return InviteResponse(
        invite_id=invite.id,
        tenant_id=invite.tenant_id,
        email=str(invite.email),
        role_code=invite.role_code,
        token=invite.token,
        status=invite.status,
        expires_at=invite.expires_at,
    )


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(principal: Principal = Depends(get_current_principal)) -> TenantResponse:
    await ensure_default_tenant()
    tenant = await get_tenant_repository().find_by_id(principal.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return _tenant_response(tenant)


@router.get("/me/entitlements", response_model=EntitlementsResponse)
async def get_my_entitlements(
    principal: Principal = Depends(get_current_principal),
) -> EntitlementsResponse:
    tenant = await get_tenant_repository().find_by_id(principal.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    features = list(tenant.features) or list(PLAN_FEATURES.get(tenant.plan, []))
    return EntitlementsResponse(
        tenant_id=tenant.id,
        plan=tenant.plan,
        status=tenant.status,
        features=features,
        is_active=tenant.is_active and tenant.status == TenantStatus.ACTIVE,
    )


@router.post("/me/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(payload: InviteCreateRequest, principal: InviteDep) -> InviteResponse:
    result = await get_invite_user_handler().execute(
        InviteUserCommand(
            tenant_id=principal.tenant_id,
            email=str(payload.email),
            role_code=payload.role_code,
            actor=principal,
        )
    )
    return _invite_response(result.invite)


@router.get("/me/invites", response_model=list[InviteResponse])
async def list_invites(principal: InviteDep) -> list[InviteResponse]:
    invites = await get_invite_repository().find_by_tenant(principal.tenant_id)
    return [_invite_response(invite) for invite in invites]


@router.post("/invites/accept", response_model=TenantResponse)
async def accept_invite(payload: InviteAcceptRequest) -> TenantResponse:
    result = await get_accept_invite_handler().execute(
        AcceptInviteCommand(
            token=payload.token,
            username=payload.username,
            full_name=payload.full_name,
            password=payload.password,
        )
    )
    return _tenant_response(result.tenant)


@router.post("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(
    tenant_id: str, payload: SuspendRequest, principal: TenantAdminDep
) -> TenantResponse:
    result = await get_suspend_tenant_handler().execute(
        SuspendTenantCommand(tenant_id=tenant_id, actor=principal, reason=payload.reason)
    )
    return _tenant_response(result.tenant)


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(tenant_id: str, principal: TenantAdminDep) -> TenantResponse:
    result = await get_activate_tenant_handler().execute(
        ActivateTenantCommand(tenant_id=tenant_id, actor=principal)
    )
    return _tenant_response(result.tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, _user: AdminDep) -> TenantResponse:
    tenant = await get_tenant_repository().find_by_id(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return _tenant_response(tenant)
