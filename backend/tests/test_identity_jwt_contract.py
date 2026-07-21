"""Contract tests: JWT envelope and JWKS."""

from __future__ import annotations

import unittest

from jose import jwt

from src.security.jwt_keys import build_jwks, public_key_pem
from src.security.security import create_access_token, create_refresh_token, decode_refresh_token


class JwtContractTests(unittest.TestCase):
    def test_identity_token_verifies_with_public_key(self) -> None:
        token = create_access_token(
            "user-1",
            "ops@example.com",
            "operations",
            tenant_id="pacific-medical",
        )
        header = jwt.get_unverified_header(token)
        self.assertEqual(header.get("alg"), "RS256")
        claims = jwt.get_unverified_claims(token)
        self.assertEqual(claims["ver"], 2)
        self.assertEqual(claims["tenant_id"], "pacific-medical")
        self.assertIn("perm_ver", claims)

        verified = jwt.decode(
            token,
            public_key_pem(),
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        self.assertEqual(verified["sub"], "user-1")
        self.assertEqual(verified["role"], "operations")

    def test_jwks_contains_rsa_key(self) -> None:
        jwks = build_jwks()
        self.assertIn("keys", jwks)
        self.assertEqual(jwks["keys"][0]["kty"], "RSA")
        self.assertEqual(jwks["keys"][0]["alg"], "RS256")
        self.assertTrue(public_key_pem().startswith("-----BEGIN PUBLIC KEY-----"))

    def test_refresh_token_roundtrip(self) -> None:
        refresh = create_refresh_token("user-1", tenant_id="pacific-medical")
        payload = decode_refresh_token(refresh)
        self.assertEqual(payload["sub"], "user-1")
        self.assertEqual(payload["tenant_id"], "pacific-medical")
        self.assertEqual(payload["type"], "refresh")


if __name__ == "__main__":
    unittest.main()
