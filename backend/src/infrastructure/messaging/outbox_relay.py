from __future__ import annotations

import asyncio
import logging

from src.domain.events.publisher import EventPublisher
from src.domain.repositories import OutboxRepository

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5
BATCH_SIZE = 50


class OutboxRelayWorker:
    """
    Background asyncio task that polls the outbox collection and publishes
    un-sent events to Redis Streams, then marks them published.

    Guarantees at-least-once delivery.  Consumers must be idempotent.
    """

    def __init__(self, outbox_repo: OutboxRepository, publisher: EventPublisher) -> None:
        self._outbox_repo = outbox_repo
        self._publisher = publisher
        self._running = False

    async def start(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._relay_batch()
            except Exception:
                logger.exception("OutboxRelayWorker error")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def stop(self) -> None:
        self._running = False

    async def _relay_batch(self) -> None:
        records = await self._outbox_repo.find_unpublished(limit=BATCH_SIZE)
        for record in records:
            try:
                await self._publisher.publish(_OutboxEventProxy(record))
                await self._outbox_repo.mark_published(record.id)
            except Exception:
                logger.exception("Failed to relay outbox record %s", record.id)


class _OutboxEventProxy:
    """Thin wrapper so OutboxRecord can be passed to EventPublisher.publish()."""

    def __init__(self, record) -> None:
        self._record = record

    @property
    def event_type(self) -> str:
        return self._record.event_type

    def to_dict(self) -> dict:
        return self._record.payload
