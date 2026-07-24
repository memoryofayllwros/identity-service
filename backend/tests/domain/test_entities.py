"""Domain entity unit tests."""

from __future__ import annotations

import unittest

from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.domain.events import UserDeactivated, UserRegistered
from src.domain.value_objects.email import Email
from src.shared.permissions import ADMIN_PERMISSIONS


class AggregateRootEventTests(unittest.TestCase):
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
            permissions=list(ADMIN_PERMISSIONS),
        )
        events = user.collect_events()
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], UserRegistered)


class UserEntityTests(unittest.TestCase):
    def test_status_transitions(self) -> None:
        user = User(
            id="u1",
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
        )
        self.assertTrue(user.is_active)
        user.suspend()
        self.assertEqual(user.status, UserStatus.SUSPENDED)
        self.assertFalse(user.is_active)
        user.activate()
        self.assertEqual(user.status, UserStatus.ACTIVE)
        user.deactivate()
        self.assertEqual(user.status, UserStatus.DEACTIVATED)

    def test_change_password_clears_must_change_flag(self) -> None:
        user = User(
            id="u1",
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
            must_change_password=True,
        )
        user.change_password("new-hash")
        self.assertFalse(user.must_change_password)
        self.assertEqual(user.password_hash, "new-hash")


class EmailValueObjectTests(unittest.TestCase):
    def test_normalizes_email(self) -> None:
        email = Email("  User@Example.COM ")
        self.assertEqual(email.value, "user@example.com")


if __name__ == "__main__":
    unittest.main()
