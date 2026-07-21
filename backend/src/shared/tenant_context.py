"""Request-scoped tenant_id binding for Identity."""

from __future__ import annotations

from contextvars import ContextVar, Token


_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def bind_tenant_id(tenant_id: str) -> Token:
    if not tenant_id:
        raise RuntimeError("tenant_id must be non-empty")
    return _tenant_id.set(tenant_id)


def reset_tenant_id(token: Token) -> None:
    _tenant_id.reset(token)


def configured_tenant_id() -> str:
    from src.infrastructure.settings import get_settings

    return get_settings().tenant_instance_id


def current_tenant_id() -> str:
    value = _tenant_id.get()
    if value:
        return value
    return configured_tenant_id()


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
