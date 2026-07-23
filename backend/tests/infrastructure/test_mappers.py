"""Mapper round-trip tests."""

from __future__ import annotations

import unittest

from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone
from src.infrastructure.persistence.mongo._utils import new_id
from src.infrastructure.persistence.mongo.mappers import MembershipMapper, RoleMapper, UserMapper


class UserMapperTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        user = User(
            id=new_id(),
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
            phone=Phone(country_code="852", phone_number="91234567"),
        )
        doc = UserMapper.to_document(user)
        restored = UserMapper.to_domain(doc)
        self.assertEqual(restored.id, user.id)
        self.assertEqual(restored.email, user.email)
        self.assertIsNotNone(restored.phone)
        assert restored.phone is not None
        self.assertEqual(restored.phone.digits(), "85291234567")


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


class MembershipMapperTests(unittest.TestCase):
    def test_role_enum_preserved(self) -> None:
        from src.domain.entities.membership import Membership

        membership = Membership(
            id=new_id(),
            tenant_id="t1",
            user_id="u1",
            role=UserRole.ADMIN,
            role_ids=["r1"],
        )
        doc = MembershipMapper.to_document(membership)
        restored = MembershipMapper.to_domain(doc)
        self.assertEqual(restored.role, UserRole.ADMIN)


if __name__ == "__main__":
    unittest.main()
