from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.events.base import DomainEvent


class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...
