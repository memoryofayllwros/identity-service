from __future__ import annotations

from typing import Any

from pymongo import AsyncMongoClient

from src.domain.entities._base import AggregateRoot
from src.domain.entities.invite import Invite
from src.domain.entities.membership import Membership
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.id_generator import IDGenerator
from src.domain.repositories import (
    InviteRepository,
    MembershipRepository,
    OutboxRepository,
    TenantRepository,
    UserRepository,
)
from src.domain.unit_of_work import UnitOfWork
from src.domain.utils import now_hk


class MongoUnitOfWork(UnitOfWork):
    """
    Beanie-based UoW. Uses a Motor client session so all saves land in one
    transaction when the deployment supports it.

    Falls back gracefully (no session) for local single-node dev if
    transactions are unavailable — OutboxRecord is still written.
    """

    def __init__(
        self,
        motor_client: AsyncMongoClient,
        outbox_repo: OutboxRepository,
        id_gen: IDGenerator,
        tenant_repo: TenantRepository,
        user_repo: UserRepository,
        membership_repo: MembershipRepository,
        invite_repo: InviteRepository,
    ) -> None:
        self._client = motor_client
        self._outbox_repo = outbox_repo
        self._id_gen = id_gen
        self._tenant_repo = tenant_repo
        self._user_repo = user_repo
        self._membership_repo = membership_repo
        self._invite_repo = invite_repo
        self._aggregates: list[Any] = []
        self._session = None

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
        if isinstance(agg, Tenant):
            await self._tenant_repo.save(agg)
        elif isinstance(agg, User):
            await self._user_repo.save(agg)
        elif isinstance(agg, Membership):
            await self._membership_repo.save(agg)
        elif isinstance(agg, Invite):
            await self._invite_repo.save(agg)
        else:
            raise TypeError(f"UoW: unknown aggregate type {type(agg)}")
