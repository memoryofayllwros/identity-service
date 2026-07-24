from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes

from src.domain.enums import UserRole, UserStatus
from src.infrastructure.dependencies import (
    get_authorization_service,
    get_user_repository,
)
from src.infrastructure.security.principal import Principal
from src.infrastructure.security.security import SecurityError, decode_access_token
from src.infrastructure.security.security_schemes import bearer_scheme, oauth2_scheme, resolve_bearer_token
from src.shared.constants import DEFAULT_TENANT_ID
from src.shared.tenant_context import bind_tenant_id


async def _extract_token(
    oauth_token: str | None = Depends(oauth2_scheme),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    return resolve_bearer_token(oauth_token, credentials)


def _principal_from_claims(payload: dict, *, bearer_token: str | None = None) -> Principal:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
    tenant_id = payload.get("tenant_id") or DEFAULT_TENANT_ID
    role_raw = payload.get("role") or UserRole.OPERATIONS.value
    try:
        role = UserRole(role_raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token role.") from exc
    email = payload.get("email") or ""
    role_ids = list(payload.get("role_ids") or [])
    perm_ver = int(payload.get("perm_ver") or 1)
    scopes = list(payload.get("scopes") or [])
    bind_tenant_id(tenant_id)
    return Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        email=email,
        role_ids=role_ids,
        perm_ver=perm_ver,
        scopes=scopes,
        bearer_token=bearer_token,
    )


async def _load_principal(token: str) -> Principal:
    """Verify JWT, ensure user is active, and resolve live permissions from user document."""
    try:
        payload = decode_access_token(token)
    except SecurityError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    principal = _principal_from_claims(payload, bearer_token=token)
    user = await get_user_repository().find_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User does not exist.")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive.")

    perms = get_authorization_service().permissions_for_user(user)
    role_code = get_authorization_service().infer_role_from_permissions(list(perms))
    role = UserRole.ADMIN if role_code == UserRole.ADMIN.value else UserRole.OPERATIONS
    principal = Principal(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        role=role,
        email=user.email.value,
        full_name=user.full_name,
        role_ids=[],
        perm_ver=1,
        scopes=list(perms)[:32],
        permissions=frozenset(perms),
        bearer_token=token,
    )
    bind_tenant_id(principal.tenant_id)
    return principal


async def get_current_principal(
    security_scopes: SecurityScopes,
    token: str | None = Depends(_extract_token),
) -> Principal:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    try:
        from jose import jwt as jose_jwt

        payload = jose_jwt.get_unverified_claims(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    _validate_security_scopes(security_scopes, payload)
    return await _load_principal(token)


async def get_current_user(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """Back-compat name — returns Principal (claims), not UserDoc."""
    return principal


async def get_optional_principal(token: str | None = Depends(_extract_token)) -> Principal | None:
    if token is None:
        return None
    return await _load_principal(token)


async def get_optional_user(token: str | None = Depends(_extract_token)) -> Principal | None:
    return await get_optional_principal(token)


def _validate_security_scopes(security_scopes: SecurityScopes, payload: dict) -> None:
    required_scopes = security_scopes.scopes
    if not required_scopes:
        return

    token_scopes = set(payload.get("scopes") or _role_scopes(payload.get("role")))
    missing_scopes = [scope for scope in required_scopes if scope not in token_scopes]
    if not missing_scopes:
        return

    authenticate_value = (
        f'Bearer scope="{security_scopes.scope_str}"'
        if security_scopes.scope_str
        else "Bearer"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions",
        headers={"WWW-Authenticate": authenticate_value},
    )


def _role_scopes(role: str | None) -> list[str]:
    if role == UserRole.ADMIN.value:
        return ["read", "write", "admin"]
    if role == UserRole.OPERATIONS.value:
        return ["read", "write"]
    return []


def require_permission(*codes: str):
    """Require at least one of the given permission codes."""

    async def permission_guard(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not codes:
            return principal
        if any(principal.has_permission(code) for code in codes):
            return principal
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    return permission_guard


def require_roles(*allowed_roles: UserRole):
    """Legacy role guard — prefer require_permission for new code."""

    async def role_guard(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.permissions:
            if principal.role in allowed_roles:
                return principal
            from src.shared.permissions import IDENTITY_USER_ADMIN

            if UserRole.ADMIN in allowed_roles and principal.has_permission(IDENTITY_USER_ADMIN):
                return principal
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        if principal.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")
        return principal

    return role_guard


def require_roles_principal(*allowed_roles: UserRole):
    return require_roles(*allowed_roles)
