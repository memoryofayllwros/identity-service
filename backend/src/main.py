"""Identity Platform service entrypoint."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

os.environ.setdefault("SERVICE_NAME", "identity")

from src.api.identity_routers import IDENTITY_ROUTERS, jwks_router
from src.domain.exceptions import (
    DomainError,
    DuplicateEmail,
    DuplicateTenantSlug,
    DuplicateUsername,
    Forbidden,
    InvalidCredentials,
    InvalidRoleCode,
    InvalidToken,
    InviteExpired,
    InviteNotFound,
    InviteNotPending,
    MembershipInactive,
    RegistrationClosed,
    TenantAlreadySuspended,
    TenantNotFound,
    TenantNotSuspended,
    TenantSuspended,
    UserInactive,
    UserNotFound,
)
from src.infrastructure.database import close_database, init_database
from src.infrastructure.dependencies import (
    build_event_publisher,
    ensure_default_tenant,
    ensure_platform_role_templates,
    get_outbox_relay_worker,
    reset_event_publisher,
)
from src.infrastructure.settings import get_settings, validate_deployment_tenant
from src.services.base import format_duplicate_key_error


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_settings.cache_clear()
    reset_event_publisher()
    settings = get_settings()
    validate_deployment_tenant(settings)
    await init_database()
    build_event_publisher()
    await ensure_platform_role_templates()
    await ensure_default_tenant()
    relay = get_outbox_relay_worker()
    relay_task = asyncio.create_task(relay.start())
    yield
    relay.stop()
    relay_task.cancel()
    try:
        await relay_task
    except asyncio.CancelledError:
        pass
    await close_database()


app = FastAPI(
    title="Pacific Identity Platform API",
    version="0.3.0",
    lifespan=lifespan,
)

for router in IDENTITY_ROUTERS:
    if router is jwks_router:
        continue
    app.include_router(router, prefix="/api")

app.include_router(jwks_router)
app.include_router(jwks_router, prefix="/api")


_DOMAIN_STATUS: dict[type[DomainError], int] = {
    DuplicateEmail: status.HTTP_409_CONFLICT,
    DuplicateUsername: status.HTTP_409_CONFLICT,
    DuplicateTenantSlug: status.HTTP_409_CONFLICT,
    InviteExpired: status.HTTP_410_GONE,
    InviteNotFound: status.HTTP_404_NOT_FOUND,
    InviteNotPending: status.HTTP_404_NOT_FOUND,
    RegistrationClosed: status.HTTP_403_FORBIDDEN,
    TenantAlreadySuspended: status.HTTP_409_CONFLICT,
    TenantNotFound: status.HTTP_404_NOT_FOUND,
    TenantNotSuspended: status.HTTP_409_CONFLICT,
    TenantSuspended: status.HTTP_403_FORBIDDEN,
    UserInactive: status.HTTP_401_UNAUTHORIZED,
    UserNotFound: status.HTTP_404_NOT_FOUND,
    InvalidCredentials: status.HTTP_401_UNAUTHORIZED,
    InvalidToken: status.HTTP_401_UNAUTHORIZED,
    MembershipInactive: status.HTTP_401_UNAUTHORIZED,
    Forbidden: status.HTTP_403_FORBIDDEN,
    InvalidRoleCode: status.HTTP_400_BAD_REQUEST,
}


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    status_code = _DOMAIN_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc) or type(exc).__name__},
    )


@app.exception_handler(DuplicateKeyError)
async def duplicate_key_error_handler(_request: Request, exc: DuplicateKeyError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": format_duplicate_key_error(exc)},
    )


@app.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "identity-platform",
        "env": settings.app_env,
        "tenant_instance_id": settings.tenant_instance_id,
        "docs": "/docs",
        "jwks": "/.well-known/jwks.json",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8001, reload=True)
