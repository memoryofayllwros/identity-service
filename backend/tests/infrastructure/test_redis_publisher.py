"""Redis Streams publisher tests."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from src.domain.events import TenantCreated
from src.infrastructure.messaging.redis_streams import RedisStreamsPublisher


class RedisStreamsPublisherTests(unittest.IsolatedAsyncioTestCase):
    async def test_publish_calls_xadd(self) -> None:
        redis = MagicMock()
        redis.xadd = AsyncMock()
        publisher = RedisStreamsPublisher(redis, "identity:events")
        event = TenantCreated(tenant_id="t1", name="Acme", slug="acme")
        await publisher.publish(event)
        redis.xadd.assert_awaited_once()
        args, _kwargs = redis.xadd.await_args
        self.assertEqual(args[0], "identity:events")


if __name__ == "__main__":
    unittest.main()
