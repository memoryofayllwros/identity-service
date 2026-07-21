"""Identity Platform service entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError

os.environ.setdefault("SERVICE_NAME", "identity")

from src.api.identity_routers import IDENTITY_ROUTERS, jwks_router
from src.infrastructure.database import close_database, init_database
from src.infrastructure.settings import get_settings, validate_deployment_tenant
from src.services.auth_service import ensure_default_tenant
from src.services.base import format_duplicate_key_error
from src.services.rbac_service import ensure_platform_role_templates


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_settings.cache_clear()
    settings = get_settings()
    validate_deployment_tenant(settings)
    await init_database()
    await ensure_platform_role_templates()
    await ensure_default_tenant()
    yield
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
