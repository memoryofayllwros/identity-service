from __future__ import annotations

from typing import Any

from src.domain.entities._base import AggregateRoot
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.entities.user import User
from src.domain.id_generator import IDGenerator
from src.domain.repositories import OutboxRepository, UserRepository
from src.domain.unit_of_work import UnitOfWork
from src.domain.utils import now_hk


class MongoUnitOfWork(UnitOfWork):
    def __init__(
        self,
        outbox_repo: OutboxRepository,
        id_gen: IDGenerator,
        user_repo: UserRepository,
    ) -> None:
        self._outbox_repo = outbox_repo
        self._id_gen = id_gen
        self._user_repo = user_repo
        self._aggregates: list[Any] = []

    def register(self, aggregate: Any) -> None:
        self._aggregates.append(aggregate)

    async def commit(self) -> None:
        all_events = []
        for agg in self._aggregates:
            if isinstance(agg, AggregateRoot):
                all_events.extend(agg.collect_events())

        for agg in self._aggregates:
            await self._save_aggregate(agg)

        for event in all_events:
            record = OutboxRecord(
                id=self._id_gen(),
                event_type=event.event_type,
                payload=event.to_dict(),
                created_at=now_hk(),
            )
            await self._outbox_repo.save(record)

        self._aggregates = []

    async def rollback(self) -> None:
        for agg in self._aggregates:
            if isinstance(agg, AggregateRoot):
                agg.collect_events()
        self._aggregates = []

    async def _save_aggregate(self, agg: Any) -> None:
        if isinstance(agg, User):
            await self._user_repo.save(agg)
        else:
            raise TypeError(f"UoW: unknown aggregate type {type(agg)}")
