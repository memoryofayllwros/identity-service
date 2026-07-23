"""OutboxRelayWorker tests."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

import pytest

from src.domain.entities.outbox_record import OutboxRecord
from src.domain.events.publisher import EventPublisher
from src.infrastructure.messaging.outbox_relay import OutboxRelayWorker
from src.domain.utils import now_hk
from src.infrastructure.persistence.mongo._utils import new_id


class _FakeOutboxRepository:
    def __init__(self, records: list[OutboxRecord]) -> None:
        self._records = records
        self.published: list[str] = []

    async def find_unpublished(self, limit: int = 50) -> list[OutboxRecord]:
        return [record for record in self._records if not record.published][:limit]

    async def save(self, record: OutboxRecord) -> None:
        self._records.append(record)

    async def mark_published(self, record_id: str) -> None:
        self.published.append(record_id)
        for record in self._records:
            if record.id == record_id:
                record.published = True


class _FakePublisher(EventPublisher):
    def __init__(self) -> None:
        self.published: list[object] = []
        self.fail_for: set[str] = set()

    async def publish(self, event) -> None:
        if event.event_type in self.fail_for:
            raise RuntimeError("publish failed")
        self.published.append(event)


@pytest.mark.asyncio
class OutboxRelayWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_relay_batch_publishes_and_marks_records(self) -> None:
        record = OutboxRecord(
            id=new_id(),
            event_type="TenantCreated",
            payload={"type": "TenantCreated", "tenant_id": "t1"},
            created_at=now_hk(),
        )
        repo = _FakeOutboxRepository([record])
        publisher = _FakePublisher()
        worker = OutboxRelayWorker(repo, publisher)

        await worker._relay_batch()

        self.assertEqual(len(publisher.published), 1)
        self.assertEqual(repo.published, [record.id])
        self.assertTrue(record.published)

    async def test_relay_batch_continues_after_single_failure(self) -> None:
        first = OutboxRecord(
            id=new_id(),
            event_type="TenantCreated",
            payload={"type": "TenantCreated", "tenant_id": "t1"},
            created_at=now_hk(),
        )
        second = OutboxRecord(
            id=new_id(),
            event_type="UserRegistered",
            payload={"type": "UserRegistered", "user_id": "u1"},
            created_at=now_hk(),
        )
        repo = _FakeOutboxRepository([first, second])
        publisher = _FakePublisher()
        publisher.fail_for.add("TenantCreated")
        worker = OutboxRelayWorker(repo, publisher)

        await worker._relay_batch()

        self.assertEqual(len(publisher.published), 1)
        self.assertEqual(repo.published, [second.id])
        self.assertFalse(first.published)
        self.assertTrue(second.published)


if __name__ == "__main__":
    unittest.main()
