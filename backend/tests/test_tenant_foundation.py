"""Smoke tests for Phase 1 tenant foundation."""

import unittest

from jose import jwt

from src.infrastructure.security.security import create_access_token
from src.shared.constants import DEFAULT_TENANT_ID
from src.shared.events import UserInvited, dispatcher
from src.shared.tenant_context import bind_tenant_id, current_tenant_id


class JwtTenantClaimsTests(unittest.TestCase):
    def test_access_token_includes_tenant_id(self) -> None:
        token = create_access_token(
            "user-1",
            "ops@example.com",
            "operations",
            tenant_id="tenant-acme",
        )
        claims = jwt.get_unverified_claims(token)
        self.assertEqual(claims["sub"], "user-1")
        self.assertEqual(claims["tenant_id"], "tenant-acme")
        self.assertEqual(claims["role"], "operations")


class TenantContextTests(unittest.TestCase):
    def test_bind_overrides_default(self) -> None:
        self.assertEqual(current_tenant_id(), DEFAULT_TENANT_ID)
        token = bind_tenant_id("other-tenant")
        try:
            self.assertEqual(current_tenant_id(), "other-tenant")
        finally:
            from src.shared.tenant_context import reset_tenant_id

            reset_tenant_id(token)


class DomainEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_dispatcher_invokes_subscriber(self) -> None:
        seen: list[UserInvited] = []

        async def handler(event: UserInvited) -> None:
            seen.append(event)

        dispatcher.subscribe(UserInvited, handler)
        await dispatcher.publish(UserInvited(tenant_id="t1", user_id="u1", role="admin"))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].user_id, "u1")


if __name__ == "__main__":
    unittest.main()
