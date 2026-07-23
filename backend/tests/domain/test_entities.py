"""Domain entity unit tests."""

from __future__ import annotations

import unittest
from datetime import timedelta

from src.domain.entities.invite import Invite
from src.domain.entities.tenant import Tenant
from src.domain.enums import TenantStatus
from src.domain.exceptions import InviteExpired, TenantAlreadySuspended
from src.domain.utils import now_hk
from src.domain.value_objects.email import Email
from src.infrastructure.persistence.mongo._utils import new_id


class TenantEntityTests(unittest.TestCase):
    def test_suspend_changes_status(self) -> None:
        tenant = Tenant(id="t1", name="Acme", slug="acme")
        tenant.suspend()
        self.assertEqual(tenant.status, TenantStatus.SUSPENDED)
        self.assertFalse(tenant.is_active)
        self.assertIsNotNone(tenant.suspended_at)

    def test_suspend_twice_raises(self) -> None:
        tenant = Tenant(id="t1", name="Acme", slug="acme")
        tenant.suspend()
        with self.assertRaises(TenantAlreadySuspended):
            tenant.suspend()

    def test_bump_perm_ver(self) -> None:
        tenant = Tenant(id="t1", name="Acme", slug="acme", perm_ver=1)
        self.assertEqual(tenant.bump_perm_ver(), 2)
        self.assertEqual(tenant.perm_ver, 2)


class InviteEntityTests(unittest.TestCase):
    def test_expired_invite_raises_on_accept(self) -> None:
        invite = Invite(
            id=new_id(),
            tenant_id="t1",
            email=Email("a@b.c"),
            token="tok",
            expires_at=now_hk() - timedelta(days=1),
        )
        with self.assertRaises(InviteExpired):
            invite.accept()


class EmailValueObjectTests(unittest.TestCase):
    def test_normalizes_email(self) -> None:
        email = Email("  User@Example.COM ")
        self.assertEqual(email.value, "user@example.com")


if __name__ == "__main__":
    unittest.main()
