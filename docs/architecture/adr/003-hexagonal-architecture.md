# ADR-003: Hexagonal Architecture for Identity Service

## Status

Accepted

## Context

After ADR-002 extracted Identity into `pacific-identity-platform`, the codebase used a **Service + Beanie ODM** pattern: API routes and service functions operated directly on `UserDoc`, `TenantDoc`, and related Mongo documents. This blurred persistence models with domain logic and made RBAC, invites, and tenant lifecycle hard to test in isolation.

## Decision

Adopt **Hexagonal Architecture (Ports & Adapters)** with three layers:

1. **Domain** (`backend/src/domain/`) — entities, value objects, domain events, repository interfaces. No Beanie, FastAPI, or Redis imports.
2. **Application** (`backend/src/application/`) — command/query handlers and orchestration services (`AuthorizationService`, `MembershipService`, `AuthApplicationService`).
3. **Infrastructure** (`backend/src/infrastructure/`) — Mongo persistence (documents, mappers, repositories), JWT/security adapters (`infrastructure/security/`), Redis Streams event publisher, FastAPI DI factories.

API routes remain thin adapters that delegate to application handlers. The HTTP/JWT contract in `IDENTITY_CONTRACT.md` is unchanged.

### Persistence

- Beanie documents live in `infrastructure/persistence/mongo/documents/`.
- All callers use domain entities and repositories directly. The `backend/src/models/` shim directory has been removed.

### Events

- Domain events defined in `domain/events/`.
- `EventPublisher` port in `domain/events/publisher.py` with `InProcessEventPublisher` (default) and `RedisStreamsPublisher` (production via `EVENT_TRANSPORT=redis_streams`).
- Composite publisher fan-out to in-process handlers and Redis Streams.

### Legacy cleanup

- Removed `UserDoc.role`; role lives on `MembershipDoc` only.
- Deleted `services/auth_service.py`, `rbac_service.py`, `audit_service.py`.
- Deleted `backend/src/models/` compatibility shim directory; all imports now resolve to `domain.*` or `infrastructure.persistence.mongo.*`.

## Consequences

- Positive: Domain rules testable without MongoDB; persistence swappable; clear bounded context.
- Positive: Application layer has zero FastAPI/framework imports; domain exceptions are translated to HTTP at the boundary in `main.py`.
- Positive: EventPublisher port lives in `domain/events/publisher.py` alongside the events it publishes.
- Positive: Application layer has zero `infrastructure.*` imports; auth crypto and deployment config are injected via `application/ports/` and `application/config.py`.
- Positive: `Principal` lives in `application/principal.py`; JWT/password adapters remain in `infrastructure/security/`.
- Negative: `backend/src/security/` compatibility shim removed; callers must use `infrastructure.security` or `application.principal`.
- Positive: Strangler Fig migration — handlers replace services incrementally without API breaks.
- Negative: More files and mapping boilerplate (entity ↔ document).
- Negative: Tracking consumers must implement Redis Stream subscribers separately.

## Related

- ADR-002: Identity boundary and repository extraction
- `docs/architecture/EVENT_CONTRACT.md`
- `docs/architecture/IDENTITY_CONTRACT.md`
