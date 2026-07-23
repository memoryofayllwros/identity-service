"""Domain entity unit tests."""

from __future__ import annotations

import unittest
from datetime import timedelta

from src.domain.entities.invite import Invite
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import TenantStatus
from src.domain.events import (
    InviteAccepted,
    InviteCreated,
    TenantActivated,
    TenantCreated,
    TenantSuspended,
    UserDeactivated,
    UserRegistered,
)
from src.domain.exceptions import InviteExpired, InviteNotPending, TenantAlreadySuspended
from src.domain.utils import now_hk
from src.domain.value_objects.email import Email
from src.infrastructure.persistence.mongo._utils import new_id


class AggregateRootEventTests(unittest.TestCase):
    def test_collect_events_drains_pending_events(self) -> None:
        tenant = Tenant.create(
            tenant_id="t1",
            name="Acme",
            slug="acme",
        )
        events = tenant.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TenantCreated)
        self.assertEqual(tenant.collect_events(), [])

    def test_tenant_suspend_emits_event(self) -> None:
        tenant = Tenant(id="t1", name="Acme", slug="acme")
        tenant.suspend(reason="billing")
        events = tenant.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TenantSuspended)
        self.assertEqual(events[0].reason, "billing")

    def test_tenant_activate_emits_event(self) -> None:
        tenant = Tenant(id="t1", name="Acme", slug="acme")
        tenant.suspend()
        tenant.collect_events()
        tenant.activate()
        events = tenant.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TenantActivated)

    def test_user_deactivate_emits_event(self) -> None:
        user = User(
            id="u1",
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
        )
        user.deactivate()
        events = user.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], UserDeactivated)

    def test_user_register_emits_event(self) -> None:
        user = User.register(
            user_id="u1",
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
            tenant_id="t1",
        )
        events = user.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], UserRegistered)


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
    def test_create_emits_invite_created(self) -> None:
        invite = Invite.create(
            invite_id=new_id(),
            tenant_id="t1",
            email="a@b.c",
            token="tok",
            role_code="admin",
            invited_by_user_id="admin-1",
        )
        events = invite.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], InviteCreated)

    def test_accept_emits_invite_accepted(self) -> None:
        invite = Invite.create(
            invite_id=new_id(),
            tenant_id="t1",
            email="a@b.c",
            token="tok",
            role_code="admin",
            invited_by_user_id="admin-1",
        )
        invite.collect_events()
        invite.accept(user_id="user-1")
        events = invite.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], InviteAccepted)
        self.assertEqual(events[0].user_id, "user-1")

    def test_expired_invite_raises_on_accept(self) -> None:
        invite = Invite(
            id=new_id(),
            tenant_id="t1",
            email=Email("a@b.c"),
            token="tok",
            expires_at=now_hk() - timedelta(days=1),
        )
        with self.assertRaises(InviteExpired):
            invite.accept(user_id="user-1")

    def test_accept_twice_raises(self) -> None:
        invite = Invite.create(
            invite_id=new_id(),
            tenant_id="t1",
            email="a@b.c",
            token="tok",
            role_code="admin",
            invited_by_user_id="admin-1",
        )
        invite.collect_events()
        invite.accept(user_id="user-1")
        invite.collect_events()
        with self.assertRaises(InviteNotPending):
            invite.accept(user_id="user-1")


class EmailValueObjectTests(unittest.TestCase):
    def test_normalizes_email(self) -> None:
        email = Email("  User@Example.COM ")
        self.assertEqual(email.value, "user@example.com")


if __name__ == "__main__":
    unittest.main()
