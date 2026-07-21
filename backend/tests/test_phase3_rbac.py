"""Phase 3 contract tests: JWT ver/perm_ver, permission guard."""

from __future__ import annotations

import unittest

from jose import jwt

from src.models.enums import UserRole
from src.security.principal import Principal
from src.security.security import JWT_CLAIM_VERSION, create_access_token
from src.shared.permissions import (
    ADMIN_PERMISSIONS,
    IDENTITY_USER_READ,
    PLATFORM_ROLE_TEMPLATES,
    TRACKING_BOOKING_WRITE,
)


class JwtPhase3ClaimTests(unittest.TestCase):
    def test_access_token_includes_perm_ver_and_role_ids(self) -> None:
        token = create_access_token(
            "user-1",
            "ops@example.com",
            "operations",
            tenant_id="pacific-medical",
            role_ids=["R_ops"],
            perm_ver=12,
            scopes=["tracking.booking.read"],
        )
        claims = jwt.get_unverified_claims(token)
        self.assertEqual(claims["ver"], JWT_CLAIM_VERSION)
        self.assertEqual(claims["perm_ver"], 12)
        self.assertEqual(claims["role_ids"], ["R_ops"])
        self.assertIn("tracking.booking.read", claims["scopes"])


class PermissionPrincipalTests(unittest.TestCase):
    def test_has_permission_from_snapshot(self) -> None:
        principal = Principal(
            user_id="u1",
            tenant_id="t1",
            role=UserRole.OPERATIONS,
            email="a@b.c",
            permissions=frozenset({TRACKING_BOOKING_WRITE}),
        )
        self.assertTrue(principal.has_permission(TRACKING_BOOKING_WRITE))
        self.assertFalse(principal.has_permission("identity.tenant.admin"))

    def test_admin_template_contains_booking_write(self) -> None:
        self.assertIn(TRACKING_BOOKING_WRITE, ADMIN_PERMISSIONS)
        self.assertIn(TRACKING_BOOKING_WRITE, PLATFORM_ROLE_TEMPLATES["admin"])

    def test_operations_template_includes_identity_user_read(self) -> None:
        self.assertIn(IDENTITY_USER_READ, PLATFORM_ROLE_TEMPLATES["operations"])


class RequirePermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_require_permission_allows_matching_code(self) -> None:
        from src.security.dependencies import require_permission

        guard = require_permission(TRACKING_BOOKING_WRITE)
        principal = Principal(
            user_id="u1",
            tenant_id="t1",
            role=UserRole.ADMIN,
            email="a@b.c",
            permissions=frozenset({TRACKING_BOOKING_WRITE}),
        )
        result = await guard(principal)  # type: ignore[misc]
        self.assertIs(result, principal)

    async def test_require_permission_denies_missing(self) -> None:
        from fastapi import HTTPException

        from src.security.dependencies import require_permission

        guard = require_permission(TRACKING_BOOKING_WRITE)
        principal = Principal(
            user_id="u1",
            tenant_id="t1",
            role=UserRole.OPERATIONS,
            email="a@b.c",
            permissions=frozenset({"tracking.booking.read"}),
        )
        with self.assertRaises(HTTPException) as ctx:
            await guard(principal)  # type: ignore[misc]
        self.assertEqual(ctx.exception.status_code, 403)


class RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        from src.security.rate_limit import clear_rate_limits

        clear_rate_limits()

    def test_rate_limit_trips_after_max_hits(self) -> None:
        from fastapi import HTTPException, Request

        from src.security.rate_limit import enforce_rate_limit

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/auth/login",
            "raw_path": b"/api/auth/login",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
        }
        request = Request(scope)
        for _ in range(3):
            enforce_rate_limit(request, suffix="test.login", max_hits=3, window_seconds=60)
        with self.assertRaises(HTTPException) as ctx:
            enforce_rate_limit(request, suffix="test.login", max_hits=3, window_seconds=60)
        self.assertEqual(ctx.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
