"""Backward-compatible in-process dispatcher."""

from src.infrastructure.dependencies import get_in_process_publisher
from src.infrastructure.messaging.event_publisher import InProcessEventPublisher

dispatcher = get_in_process_publisher()

__all__ = ["InProcessEventDispatcher", "dispatcher"]

InProcessEventDispatcher = InProcessEventPublisher
