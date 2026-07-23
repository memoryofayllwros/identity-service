from __future__ import annotations

import json
import logging

from src.domain.events.base import DomainEvent
from src.domain.events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class RedisStreamsPublisher(EventPublisher):
    def __init__(self, redis_client, stream_key: str) -> None:
        self._redis = redis_client
        self._stream_key = stream_key

    async def publish(self, event: DomainEvent) -> None:
        payload = {
            key: json.dumps(value) if not isinstance(value, str) else value
            for key, value in event.to_dict().items()
        }
        try:
            await self._redis.xadd(self._stream_key, payload)
        except Exception:
            logger.exception("Failed to publish %s to Redis stream %s", event.event_type, self._stream_key)
            raise
