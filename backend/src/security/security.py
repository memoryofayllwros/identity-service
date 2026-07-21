from datetime import timedelta

import bcrypt
from jose import JWTError, jwt

from src.infrastructure.settings import get_settings
from src.models._utils import as_hk
from src.security.jwt_keys import get_signing_keypair, private_key_pem, public_key_pem


class SecurityError(Exception):
    pass


# Claim schema: 1 = Phase 2; 2 = Phase 3 (perm_ver + role_ids)
JWT_CLAIM_VERSION = 2


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(
    subject: str,
    email: str,
    role: str,
    *,
    tenant_id: str,
    role_ids: list[str] | None = None,
    perm_ver: int = 1,
    scopes: list[str] | None = None,
) -> str:
    """Issue access token (Identity). RS256 + ver/perm_ver claims."""
    settings = get_settings()
    _, _, kid = get_signing_keypair()
    expire = as_hk() + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict = {
        "sub": subject,
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "role_ids": role_ids or [],
        "perm_ver": int(perm_ver),
        "ver": JWT_CLAIM_VERSION,
        "exp": int(expire.timestamp()),
    }
    # Early-stage dual-track: small scopes list OK; do not dump full enterprise catalog
    if scopes is not None:
        payload["scopes"] = list(scopes)[:32]
    headers = {"kid": kid, "alg": "RS256"}
    return jwt.encode(payload, private_key_pem(), algorithm="RS256", headers=headers)


def create_refresh_token(subject: str, *, tenant_id: str) -> str:
    settings = get_settings()
    expire = as_hk() + timedelta(days=7)
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,
        "type": "refresh",
        "ver": JWT_CLAIM_VERSION,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, private_key_pem(), algorithm="RS256")


def decode_access_token(token: str) -> dict:
    """Verify access token with local public key (Identity) or caller-supplied JWKS path."""
    try:
        return jwt.decode(
            token,
            public_key_pem(),
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise SecurityError("Invalid access token") from exc


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            public_key_pem(),
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise SecurityError("Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise SecurityError("Invalid refresh token type")
    return payload
