"""MongoUnitOfWork integration tests."""

from __future__ import annotations

import unittest

import pytest

from src.domain.entities.outbox_record import OutboxRecord
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.events import TenantCreated, UserRegistered
from src.domain.value_objects.email import Email
from src.infrastructure.persistence.mongo.documents import OutboxDocument, TenantDocument, UserDocument
from src.infrastructure.persistence.mongo.repositories import (
    MongoInviteRepository,
    MongoMembershipRepository,
    MongoOutboxRepository,
    MongoTenantRepository,
    MongoUserRepository,
)
from src.infrastructure.persistence.mongo.unit_of_work import MongoUnitOfWork
from src.infrastructure.persistence.mongo._utils import new_id


@pytest.mark.asyncio
class MongoUnitOfWorkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.uow = MongoUnitOfWork(
            motor_client=object(),
            outbox_repo=MongoOutboxRepository(),
            id_gen=new_id,
            tenant_repo=MongoTenantRepository(),
            user_repo=MongoUserRepository(),
            membership_repo=MongoMembershipRepository(),
            invite_repo=MongoInviteRepository(),
        )

    async def test_commit_saves_aggregates_and_outbox_records(self) -> None:
        tenant = Tenant.create(
            tenant_id=new_id(),
            name="Acme",
            slug="acme",
        )
        user = User.register(
            user_id=new_id(),
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
            tenant_id=tenant.id,
        )

        async with self.uow:
            self.uow.register(tenant)
            self.uow.register(user)
            await self.uow.commit()

        tenant_doc = await TenantDocument.find_one(TenantDocument.tenant_id == tenant.id)
        user_doc = await UserDocument.find_one(UserDocument.user_id == user.id)
        outbox_docs = await OutboxDocument.find_all().to_list()

        self.assertIsNotNone(tenant_doc)
        self.assertIsNotNone(user_doc)
        self.assertGreaterEqual(len(outbox_docs), 2)
        event_types = {doc.event_type for doc in outbox_docs}
        self.assertIn(TenantCreated.__name__, event_types)
        self.assertIn(UserRegistered.__name__, event_types)

    async def test_rollback_discards_pending_aggregates_and_events(self) -> None:
        tenant = Tenant.create(
            tenant_id=new_id(),
            name="Rollback",
            slug="rollback",
        )

        async with self.uow:
            self.uow.register(tenant)
            await self.uow.rollback()

        tenant_doc = await TenantDocument.find_one(TenantDocument.tenant_id == tenant.id)
        outbox_docs = await OutboxDocument.find_all().to_list()
        self.assertIsNone(tenant_doc)
        self.assertEqual(outbox_docs, [])


if __name__ == "__main__":
    unittest.main()
