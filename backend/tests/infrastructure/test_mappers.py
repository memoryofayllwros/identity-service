"""Mapper round-trip tests."""

from __future__ import annotations

import unittest

from src.domain.entities.user import User
from src.domain.enums import UserStatus
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone
from src.infrastructure.persistence.mongo._utils import new_id
from src.infrastructure.persistence.mongo.mappers import RoleMapper, UserMapper


class UserMapperTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        user = User(
            id=new_id(),
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
            phone=Phone(country_code="852", phone_number="91234567"),
            position="Engineer",
            permissions=["identity.user.read"],
            must_change_password=True,
            status=UserStatus.ACTIVE,
        )
        doc = UserMapper.to_document(user)
        restored = UserMapper.to_domain(doc)
        self.assertEqual(restored.id, user.id)
        self.assertEqual(restored.email, user.email)
        self.assertEqual(restored.position, "Engineer")
        self.assertEqual(restored.permissions, ["identity.user.read"])
        self.assertTrue(restored.must_change_password)
        self.assertIsNotNone(restored.phone)
        assert restored.phone is not None
        self.assertEqual(restored.phone.mobile(), "+85291234567")


class RoleMapperTests(unittest.TestCase):
    def test_to_document_defaults_created_at(self) -> None:
        from src.domain.entities.role import Role

        role = Role(
            id=new_id(),
            code="admin",
            name="Admin",
            permissions=["identity.user.admin"],
        )
        doc = RoleMapper.to_document(role)
        self.assertIsNotNone(doc.created_at)


if __name__ == "__main__":
    unittest.main()
