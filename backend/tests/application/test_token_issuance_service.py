"""TokenIssuanceService unit tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.application.services.token_issuance_service import TokenIssuanceService
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.value_objects.email import Email
from src.shared.constants import DEFAULT_TENANT_ID
from src.shared.permissions import IDENTITY_USER_ADMIN


class TokenIssuanceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_issue_login_produces_login_result(self) -> None:
        authz = MagicMock()
        authz.permissions_for_user.return_value = [IDENTITY_USER_ADMIN, "identity.user.read"]

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
            permissions=[IDENTITY_USER_ADMIN, "identity.user.read"],
        )

        result = await service.issue_login(user)

        self.assertEqual(result.access_token, "access-token")
        self.assertEqual(result.refresh_token, "refresh-token")
        self.assertEqual(result.expires_in_seconds, 1800)
        self.assertEqual(result.user.id, "u1")
        self.assertEqual(result.user.role, UserRole.ADMIN)
        token_service.create_access_token.assert_called_once_with(
            "u1",
            "alice@example.com",
            UserRole.ADMIN.value,
            tenant_id=DEFAULT_TENANT_ID,
            role_ids=[],
            perm_ver=1,
            scopes=[IDENTITY_USER_ADMIN, "identity.user.read"],
        )


if __name__ == "__main__":
    unittest.main()
