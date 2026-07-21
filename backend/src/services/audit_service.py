"""Auth audit logging helpers."""

from __future__ import annotations

from typing import Any

from src.models.auth_event_doc import AuthEventDoc


async def record_auth_event(
    event_type: str,
    *,
    tenant_id: str | None = None,
    user_id: str | None = None,
    actor_user_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuthEventDoc:
    doc = AuthEventDoc(
        event_type=event_type,
        tenant_id=tenant_id,
        user_id=user_id,
        actor_user_id=actor_user_id,
        detail=detail or {},
    )
    await doc.insert()
    return doc
