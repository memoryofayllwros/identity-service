"""In-process event dispatcher (Phase 1)."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.shared.events.types import DomainEvent

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=DomainEvent)
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class InProcessEventDispatcher:
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


# Process-wide dispatcher (swap transport in Phase 2/3 behind same API).
dispatcher = InProcessEventDispatcher()
