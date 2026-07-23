"""TokenIssuanceService unit tests."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.application.services.token_issuance_service import TokenIssuanceService
from src.domain.entities.membership import Membership
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.value_objects.email import Email


class TokenIssuanceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_issue_login_produces_login_result(self) -> None:
        authz = MagicMock()
        authz.permissions_for_membership = AsyncMock(return_value=["identity.user.read"])
        authz.membership_perm_ver = AsyncMock(return_value=2)

        token_service = MagicMock()
        token_service.create_access_token.return_value = "access-token"
        token_service.create_refresh_token.return_value = "refresh-token"

        service = TokenIssuanceService(
            authz=authz,
            token_service=token_service,
            jwt_expire_minutes=30,
        )
        user = User(
            id="u1",
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
        )
        membership = Membership(
            id="m1",
            tenant_id="t1",
            user_id="u1",
            role=UserRole.ADMIN,
            role_ids=["r1"],
            perm_ver=2,
        )
        tenant = Tenant(id="t1", name="Acme", slug="acme")

        result = await service.issue_login(user, membership, tenant)

        self.assertEqual(result.access_token, "access-token")
        self.assertEqual(result.refresh_token, "refresh-token")
        self.assertEqual(result.expires_in_seconds, 1800)
        self.assertEqual(result.user.id, "u1")
        self.assertEqual(result.user.tenant_id, "t1")
        token_service.create_access_token.assert_called_once()


if __name__ == "__main__":
    unittest.main()
