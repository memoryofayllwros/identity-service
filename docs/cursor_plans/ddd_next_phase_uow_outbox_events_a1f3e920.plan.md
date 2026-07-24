# DDD Next Phase — Unit of Work · Outbox · Aggregate Events · Service Decomposition

**Created:** 2026-07-23  
**Status:** DRAFT  
**Scope:** `backend/src/`  
**Goal:** Advance the service from ~8.8/10 to production-grade DDD by filling the four remaining structural gaps identified in the architecture review.

---

## Current State Summary

| Layer | State |
|---|---|
| Controller | ✅ Done |
| Application Handler | ✅ Done |
| Application Service | 🟡 `AuthApplicationService` over-responsible |
| Domain Aggregate | 🟡 No internal event collection |
| Repository Port | ✅ Done |
| Infrastructure Adapter | ✅ Done |
| Mapper | ✅ Done |
| Domain Event | 🟡 Events emitted from handlers, not aggregates |
| Unit of Work | ❌ Missing |
| Outbox | ❌ Missing |

---

## Four Gaps to Close

### Gap A — Aggregate Event Collection
**Problem:** `AggregateRoot` is a marker class. Events are published directly inside
Application Handlers (`await self.publisher.publish(TenantCreated(…))`). This means
business-significant state changes cannot produce their own events; the handler must know
*which* events to emit.

**Target:**
```
tenant.suspend()
  └─► appends TenantSuspended to self._events

handler calls uow.commit()
  └─► UoW drains aggregate._events → publishes or outboxes them
```

---

### Gap B — Unit of Work
**Problem:** Multi-aggregate saves (e.g. `RegisterTenantHandler` saves `Tenant`, `User`,
`Membership` in three separate `await repo.save()` calls) are not atomic. A failure between
saves leaves data in a partially written state.

**Target:**
```python
async with uow:
    uow.register(tenant)
    uow.register(user)
    uow.register(membership)
    await uow.commit()   # single mongo session, drains events → outbox
```

---

### Gap C — Transactional Outbox
**Problem:** `RedisStreamsPublisher` fires immediately on `publish()`. If Redis is
unavailable after the Mongo write has committed, the event is silently lost.

**Target:**
```
Mongo Transaction
  ├─ save Tenant
  ├─ save User
  ├─ save Membership
  └─ insert OutboxRecord(s)     ← same transaction

Background Relay Worker (asyncio task)
  └─ poll OutboxRecord WHERE published=False
        └─ publish to Redis Streams
              └─ mark OutboxRecord.published=True
```

---

### Gap D — AuthApplicationService Decomposition
**Problem:** `AuthApplicationService` owns login, refresh, register, profile-update,
password-reset, and token issuance. SRP is strained; future command handlers must
depend on the entire god-service to access token issuance.

**Target:**
```
TokenIssuanceService   ← issue_login(), used by Login/Register/Refresh handlers
RegistrationService    ← first-user registration bootstrap (used by AuthAppService.register)
AuthApplicationService ← slim: login(), refresh(), update_profile(), request_password_reset()
```

---

## Implementation Plan

---

### Phase 1 — Aggregate Event Collection

**Effort:** Small (~1 hour)  
**Risk:** Low — additive change, no existing tests broken  
**Dependencies:** None

#### Step 1.1 — Enhance `AggregateRoot`

**File:** `backend/src/domain/entities/_base.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from src.domain.events.base import DomainEvent


@dataclass
class AggregateRoot:
    """
    Base for all aggregate roots.

    Rules:
    - Cross-aggregate references use IDs (str), never object references.
    - Mutations go through the aggregate root; no direct mutation of inner
      entities from outside the aggregate boundary.
    - State-changing methods append domain events to _events; the Unit of Work
      drains these after commit.
    """
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False, compare=False)

    def collect_events(self) -> list[DomainEvent]:
        """Drain and return all pending domain events."""
        events, self._events = self._events, []
        return events

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)
```

#### Step 1.2 — Wire events into `Tenant`

**File:** `backend/src/domain/entities/tenant.py`

Add `_record()` calls inside state-transition methods:

```python
def suspend(self) -> None:
    if self.status == TenantStatus.SUSPENDED:
        raise TenantAlreadySuspended()
    self.status = TenantStatus.SUSPENDED
    self.is_active = False
    self.suspended_at = now_hk()
    self._record(TenantSuspended(tenant_id=self.id))  # NEW

def activate(self, features: list[str] | None = None) -> None:
    ...
    self._record(TenantActivated(tenant_id=self.id))  # NEW
```

> `TenantActivated` event needs to be added to `domain/events/tenant_created.py`
> (or its own file if preferred).

#### Step 1.3 — Wire events into `Invite`

**File:** `backend/src/domain/entities/invite.py`

```python
def accept(self) -> None:
    ...
    self.status = InviteStatus.ACCEPTED
    self.accepted_at = now_hk()
    self._record(InviteAccepted(invite_id=self.id, tenant_id=self.tenant_id))  # NEW

def revoke(self) -> None:
    self.status = InviteStatus.REVOKED
    self._record(InviteRevoked(invite_id=self.id, tenant_id=self.tenant_id))  # NEW
```

#### Step 1.4 — Wire events into `User`

**File:** `backend/src/domain/entities/user.py`

```python
def deactivate(self) -> None:
    self.is_active = False
    self._record(UserDeactivated(user_id=self.id))  # NEW
```

> Add `UserDeactivated` to `domain/events/user_registered.py` or its own file.

#### Step 1.5 — Update existing handlers

Handlers that currently call `await self.publisher.publish(TenantCreated(…))` directly
should instead let the aggregate produce the event and let the UoW drain it (Phase 2).
These direct publish calls will be removed in Phase 2.

---

### Phase 2 — Unit of Work

**Effort:** Medium (~2–3 hours)  
**Risk:** Medium — changes handler call sites; requires Mongo replica set or transaction mock for tests  
**Dependencies:** Phase 1

#### Step 2.1 — Define `UnitOfWork` port in domain

**New file:** `backend/src/domain/unit_of_work.py`

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class UnitOfWork(ABC):
    """
    Coordinates persistence of multiple aggregates and event dispatch.

    Usage:
        async with uow:
            uow.register(tenant)
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
        1. Persist all registered aggregates in a single session/transaction.
        2. Drain domain events from each aggregate.
        3. Write OutboxRecords for each event (same session).
        """
        ...

    @abstractmethod
    async def rollback(self) -> None: ...

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()
        # commit is explicit; no auto-commit on clean exit
```

#### Step 2.2 — `OutboxRecord` domain entity

**New file:** `backend/src/domain/entities/outbox_record.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.entities._base import AggregateRoot


@dataclass
class OutboxRecord:
    """Not an aggregate — just a persistence value object for the outbox."""
    id: str
    event_type: str
    payload: dict[str, Any]
    published: bool = False
    created_at: datetime | None = None
    published_at: datetime | None = None
```

#### Step 2.3 — `OutboxRepository` port

Add to `backend/src/domain/repositories/__init__.py`:

```python
class OutboxRepository(ABC):
    @abstractmethod
    async def save(self, record: OutboxRecord) -> None: ...

    @abstractmethod
    async def find_unpublished(self, limit: int = 50) -> list[OutboxRecord]: ...

    @abstractmethod
    async def mark_published(self, record_id: str) -> None: ...
```

#### Step 2.4 — `MongoUnitOfWork` infrastructure implementation

**New file:** `backend/src/infrastructure/persistence/mongo/unit_of_work.py`

```python
from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from src.domain.entities._base import AggregateRoot
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.unit_of_work import UnitOfWork
from src.domain.id_generator import IDGenerator
from src.domain.utils import now_hk

# Import all concrete repositories needed
from src.infrastructure.persistence.mongo.repositories import (
    MongoTenantRepository,
    MongoUserRepository,
    MongoMembershipRepository,
    ...
)


class MongoUnitOfWork(UnitOfWork):
    """
    Beanie-based UoW.  Uses a Motor client session so all saves land in one
    transaction (requires a MongoDB replica set or Atlas M10+).
    
    Falls back gracefully (no session) for local single-node dev if
    transactions are unavailable — OutboxRecord is still written.
    """

    def __init__(
        self,
        motor_client: AsyncIOMotorClient,
        outbox_repo,  # MongoOutboxRepository
        id_gen: IDGenerator,
    ) -> None:
        self._client = motor_client
        self._outbox_repo = outbox_repo
        self._id_gen = id_gen
        self._aggregates: list[Any] = []
        self._session = None

    def register(self, aggregate: Any) -> None:
        self._aggregates.append(aggregate)

    async def commit(self) -> None:
        # Collect events before any save (saves don't touch _events)
        all_events = []
        for agg in self._aggregates:
            if hasattr(agg, "collect_events"):
                all_events.extend(agg.collect_events())

        # Persist aggregates (ideally inside a session)
        for agg in self._aggregates:
            await self._save_aggregate(agg)

        # Write outbox records
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
        self._aggregates = []

    async def _save_aggregate(self, agg: Any) -> None:
        # Dispatch to correct repository by type
        from src.domain.entities.tenant import Tenant
        from src.domain.entities.user import User
        from src.domain.entities.membership import Membership
        from src.domain.entities.invite import Invite

        if isinstance(agg, Tenant):
            await MongoTenantRepository().save(agg)
        elif isinstance(agg, User):
            await MongoUserRepository().save(agg)
        elif isinstance(agg, Membership):
            await MongoMembershipRepository().save(agg)
        elif isinstance(agg, Invite):
            await MongoInviteRepository().save(agg)
        else:
            raise TypeError(f"UoW: unknown aggregate type {type(agg)}")
```

> **Implementation note:** The final implementation should inject concrete repo
> instances (not instantiate them inline) and use a Motor session for true
> atomicity. The type-dispatch table above can be a registered dict for cleanliness.

#### Step 2.5 — Update handlers to use UoW

Example — `RegisterTenantHandler`:

```python
# Before
await self.tenant_repo.save(tenant)
await self.user_repo.save(user)
...
await self.publisher.publish(TenantCreated(...))

# After
async with self.uow:
    self.uow.register(tenant)   # tenant.suspend() already appended TenantCreated
    self.uow.register(user)
    self.uow.register(membership)
    await self.uow.commit()     # saves + writes OutboxRecords atomically
```

Handlers affected:
- `RegisterTenantHandler`
- `AcceptInviteHandler`
- `InviteUserHandler`
- `SuspendTenantHandler`

---

### Phase 3 — Transactional Outbox

**Effort:** Medium (~2–3 hours)  
**Risk:** Low-Medium — additive background worker; failure is isolated  
**Dependencies:** Phase 2

#### Step 3.1 — `OutboxDocument` Beanie model

**Add to:** `backend/src/infrastructure/persistence/mongo/documents/__init__.py`

```python
class OutboxDocument(Document):
    record_id: str
    event_type: str
    payload: dict
    published: bool = False
    created_at: datetime | None = None
    published_at: datetime | None = None

    class Settings:
        name = "outbox"
        indexes = [
            IndexModel([("published", ASCENDING), ("created_at", ASCENDING)]),
        ]
```

#### Step 3.2 — `MongoOutboxRepository`

**Add to:** `backend/src/infrastructure/persistence/mongo/repositories/__init__.py`

```python
class MongoOutboxRepository(OutboxRepository):
    async def save(self, record: OutboxRecord) -> None:
        doc = OutboxMapper.to_document(record)
        await doc.insert()

    async def find_unpublished(self, limit: int = 50) -> list[OutboxRecord]:
        docs = (
            await OutboxDocument.find(OutboxDocument.published == False)
            .sort([("created_at", ASCENDING)])
            .limit(limit)
            .to_list()
        )
        return [OutboxMapper.to_domain(doc) for doc in docs]

    async def mark_published(self, record_id: str) -> None:
        doc = await OutboxDocument.find_one(OutboxDocument.record_id == record_id)
        if doc:
            await doc.set({"published": True, "published_at": now_hk()})
```

#### Step 3.3 — `OutboxRelayWorker`

**New file:** `backend/src/infrastructure/messaging/outbox_relay.py`

```python
from __future__ import annotations

import asyncio
import logging

from src.domain.repositories import OutboxRepository
from src.domain.events.publisher import EventPublisher

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
                # Re-hydrate a thin DomainEvent-like object for the publisher
                from src.infrastructure.messaging.outbox_relay import _OutboxEventProxy
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
```

#### Step 3.4 — Register worker in application lifespan

**File:** `backend/src/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing startup ...
    relay = OutboxRelayWorker(outbox_repo, redis_publisher)
    task = asyncio.create_task(relay.start())
    yield
    relay.stop()
    task.cancel()
```

#### Step 3.5 — Remove direct `publisher.publish()` from handlers

Once the outbox relay is running, handlers should **not** call `publisher.publish()`
directly. The UoW writes the OutboxRecord; the relay worker publishes it to Redis.

Handlers to update: same list as Phase 2 Step 2.5.

> **Migration path during transition:** keep `CompositeEventPublisher` wired
> in parallel (in-process + outbox) until outbox is proven stable, then remove
> the in-process path.

---

### Phase 4 — AuthApplicationService Decomposition

**Effort:** Small–Medium (~1–2 hours)  
**Risk:** Low — purely additive extraction, no behavioral change  
**Dependencies:** None (independent of Phases 1–3)

#### Step 4.1 — Extract `TokenIssuanceService`

**New file:** `backend/src/application/services/token_issuance_service.py`

Responsibility: given a `(User, Membership, Tenant)` triple, produce a `LoginResult`.

```python
@dataclass
class TokenIssuanceService:
    authz: AuthorizationService
    token_service: TokenService
    jwt_expire_minutes: int

    async def issue_login(
        self,
        user: User,
        membership: Membership,
        tenant: Tenant,
    ) -> LoginResult:
        perms = await self.authz.permissions_for_membership(membership)
        perm_ver = await self.authz.membership_perm_ver(membership, tenant)
        token = self.token_service.create_access_token(...)
        refresh = self.token_service.create_refresh_token(...)
        return LoginResult(...)
```

Callers updated:
- `AuthApplicationService.issue_login()` → delegates to `TokenIssuanceService`
- `RegisterTenantHandler` injects `TokenIssuanceService` instead of `AuthApplicationService`
- `AcceptInviteHandler` (if it issues tokens) → same

#### Step 4.2 — Slim down `AuthApplicationService`

After extraction, `AuthApplicationService` retains:
- `login()`
- `refresh()`
- `update_profile()`
- `request_password_reset()`

It no longer directly builds JWT payloads; it delegates to `TokenIssuanceService`.

#### Step 4.3 — Extract `RegistrationService` (optional, lower priority)

The first-user bootstrap logic in `AuthApplicationService.register()` can move to
a dedicated `RegistrationService` or handler (`RegisterFirstUserHandler`) in a
follow-up cycle.

---

## Suggested Execution Order

```
Phase 1  →  Phase 4  →  Phase 2  →  Phase 3
```

Rationale:
- Phase 1 (aggregate events) and Phase 4 (service split) are independent and low-risk; do them first.
- Phase 2 (UoW) builds on Phase 1's event collection.
- Phase 3 (outbox) builds on Phase 2's outbox records.

---

## Testing Strategy

| Phase | Test type | Focus |
|---|---|---|
| Phase 1 | Unit | `AggregateRoot.collect_events()`, `tenant.suspend()` emits `TenantSuspended` |
| Phase 1 | Unit | `invite.accept()` emits `InviteAccepted`; second call raises |
| Phase 2 | Integration | `MongoUnitOfWork.commit()` saves multiple aggregates + writes OutboxRecords |
| Phase 2 | Integration | Mid-commit failure leaves no partial state |
| Phase 3 | Integration | `OutboxRelayWorker` picks up unpublished records, marks them published |
| Phase 3 | Unit | `OutboxRelayWorker` continues after a single record's publish failure |
| Phase 4 | Unit | `TokenIssuanceService.issue_login()` produces correct `LoginResult` |
| Phase 4 | Integration | `RegisterTenantHandler` still produces valid login after wiring `TokenIssuanceService` |

---

## File Change Summary

### New files
| File | Purpose |
|---|---|
| `domain/unit_of_work.py` | UoW abstract port |
| `domain/entities/outbox_record.py` | Outbox value object |
| `application/services/token_issuance_service.py` | Extracted token logic |
| `infrastructure/persistence/mongo/unit_of_work.py` | Mongo UoW implementation |
| `infrastructure/messaging/outbox_relay.py` | Background relay worker |
| `domain/events/invite_events.py` | `InviteAccepted`, `InviteRevoked` |
| `domain/events/user_events.py` | `UserDeactivated` (+ others as needed) |
| `domain/events/tenant_events.py` | `TenantActivated` |

### Modified files
| File | Change |
|---|---|
| `domain/entities/_base.py` | Add `_events`, `collect_events()`, `_record()` |
| `domain/entities/tenant.py` | Call `_record()` in `suspend()`, `activate()` |
| `domain/entities/invite.py` | Call `_record()` in `accept()`, `revoke()` |
| `domain/entities/user.py` | Call `_record()` in `deactivate()` |
| `domain/repositories/__init__.py` | Add `OutboxRepository` |
| `infrastructure/persistence/mongo/documents/__init__.py` | Add `OutboxDocument` |
| `infrastructure/persistence/mongo/repositories/__init__.py` | Add `MongoOutboxRepository` |
| `infrastructure/persistence/mongo/mappers/__init__.py` | Add `OutboxMapper` |
| `application/commands/register_tenant.py` | Use `UoW`; inject `TokenIssuanceService` |
| `application/commands/accept_invite.py` | Use `UoW` |
| `application/commands/invite_user.py` | Use `UoW` |
| `application/commands/suspend_tenant.py` | Use `UoW` |
| `application/services/auth_application_service.py` | Slim down; delegate token issuance |
| `infrastructure/dependencies.py` | Wire new services and UoW |
| `main.py` | Register `OutboxRelayWorker` in lifespan |

---

## Constraints and Risks

| Risk | Mitigation |
|---|---|
| MongoDB transactions require replica set | Wrap session creation in try/except; fall back to non-transactional for dev, document requirement for prod |
| Outbox relay is at-least-once | Ensure all Redis Stream consumers are idempotent (use `event_id` dedup key) |
| `_events` field in dataclass | Use `field(default_factory=list, init=False, repr=False, compare=False)` to avoid breaking `__eq__`, `__hash__`, or `__init__` signatures |
| Phase 2 UoW increases coupling of infrastructure | Repository dispatch table inside UoW should use injected instances, not hard-coded class names |
| Phase 4 extraction changes DI graph | Update `infrastructure/dependencies.py` carefully; one wrong wire breaks all handlers |
