"""Identity ops: auth audit listing + billing webhook stub."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.domain.entities.auth_event import AuthEvent
from src.domain.enums import TenantStatus
from src.infrastructure.dependencies import (
    get_auth_event_repository,
    get_authorization_service,
    get_tenant_repository,
)
from src.infrastructure.persistence.mongo._utils import new_id
from src.infrastructure.security.dependencies import require_permission
from src.infrastructure.security.principal import Principal
from src.shared.permissions import IDENTITY_AUDIT_READ, IDENTITY_TENANT_ADMIN, PLAN_FEATURES

router = APIRouter(tags=["identity-ops"])
AuditDep = Annotated[
    Principal,
    Depends(require_permission(IDENTITY_AUDIT_READ, IDENTITY_TENANT_ADMIN)),
]


class AuthEventResponse(BaseModel):
    event_id: str
    event_type: str
    tenant_id: str | None = None
    user_id: str | None = None
    actor_user_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: object


@router.get("/auth/events", response_model=list[AuthEventResponse])
async def list_auth_events(
    principal: AuditDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AuthEventResponse]:
    events = await get_auth_event_repository().list_by_tenant(principal.tenant_id, limit=limit)
    return [
        AuthEventResponse(
            event_id=e.id,
            event_type=e.event_type,
            tenant_id=e.tenant_id,
            user_id=e.user_id,
            actor_user_id=e.actor_user_id,
            detail=e.detail,
            created_at=e.created_at,
        )
        for e in events
    ]


class BillingWebhookPayload(BaseModel):
    event_type: str
    tenant_id: str | None = None
    plan: str | None = None
    status: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


@router.post("/billing/webhook")
async def billing_webhook(payload: BillingWebhookPayload) -> dict[str, str]:
    authz = get_authorization_service()
    if payload.tenant_id:
        tenant = await get_tenant_repository().find_by_id(payload.tenant_id)
        if tenant is not None:
            if payload.plan:
                tenant.plan = payload.plan
                tenant.features = list(PLAN_FEATURES.get(payload.plan, tenant.features))
            if payload.status:
                if payload.status == TenantStatus.ACTIVE.value:
                    tenant.activate(features=list(tenant.features))
                else:
                    tenant.status = TenantStatus(payload.status)
                    tenant.is_active = payload.status == TenantStatus.ACTIVE.value
            await get_tenant_repository().save(tenant)
            await authz.bump_tenant_perm_ver(tenant.id)
    await get_auth_event_repository().save(
        AuthEvent.record(
            event_id=new_id(),
            event_type="billing.webhook",
            tenant_id=payload.tenant_id,
            detail={
                "event_type": payload.event_type,
                "plan": payload.plan,
                "status": payload.status,
            },
        )
    )
    return {"status": "accepted"}
