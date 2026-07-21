"""Shared auth schemes for runtime token extraction and OpenAPI / Swagger."""

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer

# OAuth2 password flow — ``username`` is mobile; token from POST /api/auth/token
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scheme_name="OAuth2Password",
    description=(
        "OAuth2 password grant. **username** = mobile (with country code), email, or account username."
    ),
    auto_error=False,
)

# Manual bearer token entry (paste JWT from /api/auth/login or /api/auth/token)
bearer_scheme = HTTPBearer(
    scheme_name="HTTPBearer",
    description="Paste a JWT access token (Bearer).",
    auto_error=False,
)


def resolve_bearer_token(
    oauth_token: str | None,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if oauth_token:
        return oauth_token
    if credentials is not None:
        return credentials.credentials
    return None
