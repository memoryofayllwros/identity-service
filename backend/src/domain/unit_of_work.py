from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class UnitOfWork(ABC):
    """
    Coordinates persistence of aggregates and event dispatch.

    Usage:
        async with uow:
            uow.register(user)
            await uow.commit()
    """

    @abstractmethod
    def register(self, aggregate: Any) -> None:
        """Track an aggregate for saving on commit."""
        ...

    @abstractmethod
    async def commit(self) -> None:
        """
        1. Persist all registered aggregates.
        2. Drain domain events from each aggregate.
        3. Write OutboxRecords for each event.
        """
        ...

    @abstractmethod
    async def rollback(self) -> None: ...

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
