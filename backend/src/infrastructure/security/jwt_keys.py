"""JWT signing keys and JWKS for Platform Core (Phase 2).

Identity signs with RS256 (private key). Tracking verifies via JWKS (public key).
Dev fallback: ephemeral RSA keypair generated at process start when PEMs unset.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from src.infrastructure.settings import get_settings


def _b64url_uint(value: int) -> str:
    length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode("ascii")


def _load_private_key(pem: str) -> RSAPrivateKey:
    key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    if not isinstance(key, RSAPrivateKey):
        raise TypeError("JWT_PRIVATE_KEY must be an RSA private key")
    return key


def _load_public_key(pem: str) -> RSAPublicKey:
    key = serialization.load_pem_public_key(pem.encode("utf-8"))
    if not isinstance(key, RSAPublicKey):
        raise TypeError("JWT_PUBLIC_KEY must be an RSA public key")
    return key


def _generate_dev_keypair() -> tuple[RSAPrivateKey, RSAPublicKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@lru_cache
def get_signing_keypair() -> tuple[RSAPrivateKey, RSAPublicKey, str]:
    """Return (private, public, kid). Cached per process."""
    settings = get_settings()
    if settings.jwt_private_key and settings.jwt_public_key:
        private_key = _load_private_key(settings.jwt_private_key)
        public_key = _load_public_key(settings.jwt_public_key)
    elif settings.jwt_private_key:
        private_key = _load_private_key(settings.jwt_private_key)
        public_key = private_key.public_key()
    else:
        private_key, public_key = _generate_dev_keypair()

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    kid = hashlib.sha256(public_pem).hexdigest()[:16]
    return private_key, public_key, kid


def private_key_pem() -> str:
    private_key, _, _ = get_signing_keypair()
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def public_key_pem() -> str:
    _, public_key, _ = get_signing_keypair()
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def build_jwks() -> dict[str, Any]:
    """Publish current (+ optional previous) RSA public keys for rotation window."""
    _, public_key, kid = get_signing_keypair()
    numbers = public_key.public_numbers()
    keys: list[dict[str, Any]] = [
        {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
            "n": _b64url_uint(numbers.n),
            "e": _b64url_uint(numbers.e),
        }
    ]
    settings = get_settings()
    if settings.jwt_previous_public_key:
        try:
            prev = _load_public_key(settings.jwt_previous_public_key)
            prev_pem = prev.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            prev_kid = hashlib.sha256(prev_pem).hexdigest()[:16]
            if prev_kid != kid:
                pn = prev.public_numbers()
                keys.append(
                    {
                        "kty": "RSA",
                        "use": "sig",
                        "alg": "RS256",
                        "kid": prev_kid,
                        "n": _b64url_uint(pn.n),
                        "e": _b64url_uint(pn.e),
                    }
                )
        except Exception:
            pass
    return {"keys": keys}
