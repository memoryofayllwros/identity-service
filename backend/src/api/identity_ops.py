"""Identity ops: auth audit listing."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.infrastructure.dependencies import get_auth_event_repository
from src.infrastructure.security.dependencies import require_permission
from src.infrastructure.security.principal import Principal
from src.shared.permissions import IDENTITY_AUDIT_READ, IDENTITY_TENANT_ADMIN

router = APIRouter(tags=["identity-ops"])
AuditDep = Annotated[
    Principal,
    Depends(require_permission(IDENTITY_AUDIT_READ, IDENTITY_TENANT_ADMIN)),
]


class AuthEventResponse(BaseModel):
    event_id: str
    event_type: str
    user_id: str | None = None
    actor_user_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: object


@router.get("/auth/events", response_model=list[AuthEventResponse])
async def list_auth_events(
    _principal: AuditDep,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AuthEventResponse]:
    events = await get_auth_event_repository().list_recent(limit=limit)
    return [
        AuthEventResponse(
            event_id=e.id,
            event_type=e.event_type,
            user_id=e.user_id,
            actor_user_id=e.actor_user_id,
            detail=e.detail,
            created_at=e.created_at,
        )
        for e in events
    ]
