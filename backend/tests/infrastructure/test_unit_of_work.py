"""MongoUnitOfWork integration tests."""

from __future__ import annotations

import unittest

import pytest

from src.domain.entities.user import User
from src.domain.events import UserRegistered
from src.domain.value_objects.email import Email
from src.infrastructure.persistence.mongo.documents import OutboxDocument, UserDocument
from src.infrastructure.persistence.mongo.repositories import (
    MongoOutboxRepository,
    MongoUserRepository,
)
from src.infrastructure.persistence.mongo.unit_of_work import MongoUnitOfWork
from src.infrastructure.persistence.mongo._utils import new_id
from src.shared.permissions import ADMIN_PERMISSIONS


@pytest.mark.asyncio
class MongoUnitOfWorkTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.uow = MongoUnitOfWork(
            outbox_repo=MongoOutboxRepository(),
            id_gen=new_id,
            user_repo=MongoUserRepository(),
        )

    async def test_commit_saves_aggregates_and_outbox_records(self) -> None:
        user = User.register(
            user_id=new_id(),
            username="alice",
            email=Email("alice@example.com"),
            full_name="Alice",
            password_hash="hash",
            permissions=list(ADMIN_PERMISSIONS),
        )

        async with self.uow:
            self.uow.register(user)
            await self.uow.commit()

        user_doc = await UserDocument.find_one(UserDocument.user_id == user.id)
        outbox_docs = await OutboxDocument.find_all().to_list()

        self.assertIsNotNone(user_doc)
        self.assertGreaterEqual(len(outbox_docs), 1)
        event_types = {doc.event_type for doc in outbox_docs}
        self.assertIn(UserRegistered.__name__, event_types)

    async def test_rollback_discards_pending_aggregates_and_events(self) -> None:
        user = User.register(
            user_id=new_id(),
            username="rollback",
            email=Email("rollback@example.com"),
            full_name="Rollback",
            password_hash="hash",
            permissions=list(ADMIN_PERMISSIONS),
        )

        async with self.uow:
            self.uow.register(user)
            await self.uow.rollback()

        user_doc = await UserDocument.find_one(UserDocument.user_id == user.id)
        outbox_docs = await OutboxDocument.find_all().to_list()
        self.assertIsNone(user_doc)
        self.assertEqual(outbox_docs, [])


if __name__ == "__main__":
    unittest.main()
