"""Request-scoped tenant_id binding for Identity."""

from __future__ import annotations

from contextvars import ContextVar, Token

_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)
_deployment_tenant_id: str | None = None


def configure_deployment_tenant_id(tenant_id: str) -> None:
    """Set the deployment default tenant (call from bootstrap at startup)."""
    global _deployment_tenant_id
    if not tenant_id:
        raise ValueError("tenant_id must be non-empty")
    _deployment_tenant_id = tenant_id


def bind_tenant_id(tenant_id: str) -> Token:
    if not tenant_id:
        raise RuntimeError("tenant_id must be non-empty")
    return _tenant_id.set(tenant_id)


def reset_tenant_id(token: Token) -> None:
    _tenant_id.reset(token)


def current_tenant_id() -> str:
    value = _tenant_id.get()
    if value:
        return value
    if _deployment_tenant_id:
        return _deployment_tenant_id
    raise RuntimeError(
        "tenant_id is not available; configure deployment tenant at startup "
        "or bind via authenticate / bind_tenant_id()"
    )


def try_current_tenant_id() -> str | None:
    return _tenant_id.get()


def require_bound_tenant_id() -> str:
    value = _tenant_id.get()
    if not value:
        raise RuntimeError(
            "tenant_id is not bound for this request; "
            "authenticate via get_current_principal or call bind_tenant_id()"
        )
    return value
