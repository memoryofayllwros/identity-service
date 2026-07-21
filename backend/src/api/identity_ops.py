"""Identity ops: auth audit listing + billing webhook stub."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.models.auth_event_doc import AuthEventDoc
from src.security.dependencies import require_permission
from src.security.principal import Principal
from src.services.audit_service import record_auth_event
from src.shared.permissions import IDENTITY_AUDIT_READ, IDENTITY_TENANT_ADMIN

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
    events = (
        await AuthEventDoc.find(AuthEventDoc.tenant_id == principal.tenant_id)
        .sort([("created_at", -1)])
        .limit(limit)
        .to_list()
    )
    return [
        AuthEventResponse(
            event_id=e.event_id,
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
    """Provider-agnostic billing hook (Stripe later)."""

    event_type: str
    tenant_id: str | None = None
    plan: str | None = None
    status: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


@router.post("/billing/webhook")
async def billing_webhook(payload: BillingWebhookPayload) -> dict[str, str]:
    """Acknowledge billing events; apply plan/status updates when tenant_id present."""
    from src.models.tenant_doc import TenantDoc
    from src.services.rbac_service import bump_tenant_perm_ver
    from src.shared.permissions import PLAN_FEATURES

    if payload.tenant_id:
        tenant = await TenantDoc.find_one(TenantDoc.tenant_id == payload.tenant_id)
        if tenant is not None:
            updates: dict[str, Any] = {}
            if payload.plan:
                updates["plan"] = payload.plan
                updates["features"] = list(PLAN_FEATURES.get(payload.plan, tenant.features))
            if payload.status:
                updates["status"] = payload.status
                updates["is_active"] = payload.status == "active"
            if updates:
                await tenant.set(updates)
                await bump_tenant_perm_ver(tenant.tenant_id)
    await record_auth_event(
        "billing.webhook",
        tenant_id=payload.tenant_id,
        detail={"event_type": payload.event_type, "plan": payload.plan, "status": payload.status},
    )
    return {"status": "accepted"}
