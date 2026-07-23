from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
import logging
from typing import TypeVar

from src.domain.events.base import DomainEvent
from src.domain.events.publisher import EventPublisher

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=DomainEvent)
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class InProcessEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    async def publish(self, event: DomainEvent) -> None:
        handlers = list(self._handlers.get(type(event), []))
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Domain event handler failed for %s: %s",
                    type(event).__name__,
                    event.to_dict(),
                )


class CompositeEventPublisher(EventPublisher):
    def __init__(self, *publishers: EventPublisher) -> None:
        self._publishers = publishers

    async def publish(self, event: DomainEvent) -> None:
        for publisher in self._publishers:
            await publisher.publish(event)
