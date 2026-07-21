"""Identity HTTP routers."""

from src.api.auth import router as auth_router
from src.modules.identity.api.tenants import router as tenants_router

# users_router lives in src.api.identity_routers (avoids circular import)

__all__ = ["auth_router", "tenants_router"]
