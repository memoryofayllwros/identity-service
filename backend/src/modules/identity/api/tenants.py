"""Identity tenant lifecycle: directory, invites, entitlements, suspend (single-tenant Phase 1)."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.models._utils import as_hk, new_id
from src.models.enums import UserRole
from src.models.invite_doc import InviteDoc
from src.models.tenant_doc import TenantDoc
from src.models.user_doc import UserDoc
from src.security.dependencies import get_current_principal, require_permission, require_roles
from src.security.principal import Principal
from src.security.security import hash_password
from src.services.audit_service import record_auth_event
from src.services.auth_service import (
    ensure_default_tenant,
    ensure_membership,
)
from src.services.base import get_identity_or_404
from src.services.rbac_service import bump_tenant_perm_ver, ensure_tenant_roles
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


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(principal: Principal = Depends(get_current_principal)) -> TenantResponse:
    await ensure_default_tenant()
    doc = await get_identity_or_404(TenantDoc, "tenant_id", principal.tenant_id)
    return TenantResponse.model_validate(doc)


@router.get("/me/entitlements", response_model=EntitlementsResponse)
async def get_my_entitlements(
    principal: Principal = Depends(get_current_principal),
) -> EntitlementsResponse:
    doc = await get_identity_or_404(TenantDoc, "tenant_id", principal.tenant_id)
    features = list(doc.features) or list(PLAN_FEATURES.get(doc.plan, []))
    return EntitlementsResponse(
        tenant_id=doc.tenant_id,
        plan=doc.plan,
        status=doc.status,
        features=features,
        is_active=doc.is_active and doc.status == "active",
    )


@router.post("/me/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(payload: InviteCreateRequest, principal: InviteDep) -> InviteResponse:
    await ensure_tenant_roles(principal.tenant_id)
    if payload.role_code not in ("admin", "operations"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role_code.")
    invite = InviteDoc(
        tenant_id=principal.tenant_id,
        email=str(payload.email).lower(),
        role_code=payload.role_code,
        token=new_id(),
        status="pending",
        invited_by_user_id=principal.user_id,
        expires_at=as_hk() + timedelta(days=7),
    )
    await invite.insert()
    await record_auth_event(
        "invite.created",
        tenant_id=principal.tenant_id,
        user_id=None,
        actor_user_id=principal.user_id,
        detail={"email": invite.email, "role_code": invite.role_code},
    )
    return InviteResponse.model_validate(invite)


@router.get("/me/invites", response_model=list[InviteResponse])
async def list_invites(principal: InviteDep) -> list[InviteResponse]:
    invites = await InviteDoc.find(
        InviteDoc.tenant_id == principal.tenant_id,
    ).to_list()
    return [InviteResponse.model_validate(i) for i in invites]


@router.post("/invites/accept", response_model=TenantResponse)
async def accept_invite(payload: InviteAcceptRequest) -> TenantResponse:
    invite = await InviteDoc.find_one(InviteDoc.token == payload.token)
    if invite is None or invite.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")
    if invite.expires_at < as_hk():
        await invite.set({"status": "expired"})
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite expired.")

    tenant = await get_identity_or_404(TenantDoc, "tenant_id", invite.tenant_id)
    if tenant.status == "suspended" or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is suspended.")

    if await UserDoc.find_one(UserDoc.email == invite.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    if await UserDoc.find_one(UserDoc.username == payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    role = UserRole.ADMIN if invite.role_code == "admin" else UserRole.OPERATIONS
    user = UserDoc(
        username=payload.username,
        email=invite.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=role,
    )
    await user.insert()
    await ensure_membership(tenant_id=tenant.tenant_id, user_id=user.user_id, role=role)
    await invite.set({"status": "accepted", "accepted_at": as_hk()})
    await bump_tenant_perm_ver(tenant.tenant_id)
    await record_auth_event(
        "invite.accepted",
        tenant_id=tenant.tenant_id,
        user_id=user.user_id,
        detail={"invite_id": invite.invite_id},
    )
    refreshed = await get_identity_or_404(TenantDoc, "tenant_id", tenant.tenant_id)
    return TenantResponse.model_validate(refreshed)


@router.post("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(tenant_id: str, payload: SuspendRequest, principal: TenantAdminDep) -> TenantResponse:
    if principal.tenant_id != tenant_id and principal.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
    doc = await get_identity_or_404(TenantDoc, "tenant_id", tenant_id)
    await doc.set(
        {
            "status": "suspended",
            "is_active": False,
            "suspended_at": as_hk(),
        }
    )
    await bump_tenant_perm_ver(tenant_id)
    await record_auth_event(
        "tenant.suspended",
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
        detail={"reason": payload.reason},
    )
    return TenantResponse.model_validate(await get_identity_or_404(TenantDoc, "tenant_id", tenant_id))


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(tenant_id: str, principal: TenantAdminDep) -> TenantResponse:
    doc = await get_identity_or_404(TenantDoc, "tenant_id", tenant_id)
    features = list(doc.features) or list(PLAN_FEATURES.get(doc.plan, []))
    await doc.set(
        {
            "status": "active",
            "is_active": True,
            "suspended_at": None,
            "features": features,
        }
    )
    await bump_tenant_perm_ver(tenant_id)
    await record_auth_event(
        "tenant.activated",
        tenant_id=tenant_id,
        actor_user_id=principal.user_id,
    )
    return TenantResponse.model_validate(await get_identity_or_404(TenantDoc, "tenant_id", tenant_id))


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, _user: AdminDep) -> TenantResponse:
    doc = await get_identity_or_404(TenantDoc, "tenant_id", tenant_id)
    return TenantResponse.model_validate(doc)
