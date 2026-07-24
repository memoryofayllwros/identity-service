# Identity Platform

Identity and access management (IAM) microservice for multi-service platforms. This service owns authentication, authorization, tenants, users, roles, memberships, and invites—nothing else.

Built with **Hexagonal Architecture** inside a **DDD bounded context**, deployed as a standalone business-capability service that other platform services (Tracking, Quotation, and others) consume over HTTP and JWT.

| | |
|---|---|
| **Stack** | Python 3.12+, FastAPI, MongoDB (Beanie), Redis Streams, RS256 JWT |
| **Version** | 0.3.0 |
| **Default port** | 8001 |

## Table of contents

- [Overview](#overview)
- [Responsibilities](#responsibilities)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API](#api)
- [Development](#development)
- [Project structure](#project-structure)
- [Architecture](#architecture)
- [Documentation](#documentation)
- [Roadmap](#roadmap)

## Overview

The platform is decomposed by business capability:

```
Platform
├── Identity Service   ← this repository
├── Tracking Service
├── Quotation Service
└── ...
```

Identity is a **bounded context**: it models users, tenants, and access control. Other services authenticate against Identity and validate permissions via JWT—they never own user or tenant data themselves.

Internally, the service follows **Hexagonal Architecture** (ports and adapters). Business rules live in the domain; HTTP, MongoDB, JWT, and messaging are implementation details pushed to the edges.

## Responsibilities

**Owned by Identity**

- User, Tenant, Role, Permission, Membership, Invite
- Authentication and authorization (JWT, RBAC)
- Domain events for identity lifecycle changes

**Not owned by Identity**

- Booking, Customer, Asset, Quotation, Inventory, and other domain concepts belong to sibling services.

## Quick start

### Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/)
- MongoDB (local or remote)
- Redis (optional; required when `EVENT_TRANSPORT=redis_streams`)

### Local development

```bash
cd backend

# Install dependencies
poetry install

# Copy and edit environment variables
cp ../deployment/.env.example .env

# Run the API
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

Health check: `GET http://localhost:8001/api/health`

Interactive API docs: `http://localhost:8001/docs`

### Docker

```bash
cd backend
docker build -t identity-service .
docker run --env-file ../deployment/.env.example -p 8001:8001 identity-service
```

## Configuration

Environment variables are defined in [`deployment/.env.example`](deployment/.env.example). Key settings:

| Variable | Description |
|----------|-------------|
| `MONGODB_URI` | MongoDB connection string |
| `IDENTITY_DATABASE_NAME` | Database name (default: `identity_db`) |
| `TENANT_INSTANCE_ID` | Immutable tenant binding for this deployment |
| `JWT_ALGORITHM` | `RS256` (recommended) |
| `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY` | RSA key pair for signing and JWKS |
| `EVENT_TRANSPORT` | `in_process` (dev) or `redis_streams` (production) |
| `REDIS_URL` | Required when using Redis Streams |

See [`docs/architecture/IDENTITY_CONTRACT.md`](docs/architecture/IDENTITY_CONTRACT.md) for the full JWT claim schema and endpoint contract.

## API

Primary routes (all prefixed with `/api` unless noted):

| Endpoint | Purpose |
|----------|---------|
| `POST /auth/login` | Issue access and refresh tokens |
| `POST /auth/refresh` | Refresh tokens; re-read membership and permissions |
| `GET /auth/me` | Current principal |
| `GET /.well-known/jwks.json` | Public keys for JWT verification |
| `POST /tenants/register` | Self-serve tenant registration |
| `POST /tenants/me/invites` | Create tenant invite |
| `POST /tenants/invites/accept` | Accept invite |
| `GET /users/{id}` | User directory lookup |
| `GET /health` | Liveness probe |

Full contract: [`docs/architecture/IDENTITY_CONTRACT.md`](docs/architecture/IDENTITY_CONTRACT.md)

## Development

### Run tests

```bash
cd backend
poetry run pytest
```

### Migrations and scripts

Utility scripts live in `backend/scripts/` (database migration, tenant export, backup). Run with Poetry from the `backend` directory.

## Project structure

```
identity-platform/
├── backend/
│   ├── src/
│   │   ├── api/              # HTTP adapters (FastAPI routers)
│   │   ├── application/      # Use cases: commands, queries, services, ports
│   │   ├── domain/           # Entities, events, repository interfaces
│   │   ├── infrastructure/   # Mongo, JWT, Redis, security adapters
│   │   ├── shared/           # Cross-cutting constants and permissions
│   │   └── main.py           # Application entrypoint
│   ├── tests/
│   ├── scripts/
│   └── pyproject.toml
├── deployment/
│   └── .env.example
└── docs/
    └── architecture/         # ADRs, contracts, schema
```

## Architecture

This service combines two ideas that solve different problems:

| Concept | Answers |
|---------|---------|
| **Microservice** | What this service owns at the platform boundary |
| **Hexagonal Architecture** | How code inside the service is organized |

### Layer overview

```
HTTP
  │
  ▼
API              ← primary adapters (receive requests, call handlers)
  │
  ▼
Application      ← orchestrate use cases (CQRS commands/queries)
  │
  ▼
Domain           ← business rules, entities, events
  ▲
  │
Infrastructure   ← Mongo repositories, JWT, Redis, mappers
```

Dependencies always point **inward**. The domain never imports FastAPI, MongoDB, JWT libraries, or Redis.

### API layer (`backend/src/api/`)

Thin HTTP adapters. They validate payloads, map requests to commands or queries, delegate to the application layer, and return responses. No business rules.

```
POST /login  →  LoginRequest  →  LoginHandler
```

### Application layer (`backend/src/application/`)

Coordinates use cases without embedding domain rules.

| Area | Role |
|------|------|
| `commands/` | State-changing use cases (`register_tenant`, `invite_user`, `accept_invite`, …) |
| `queries/` | Read-only data access (`user_queries`) |
| `services/` | Shared orchestration (`AuthApplicationService`, `AuthorizationService`, …) |
| `ports/` | Abstractions for infrastructure (`PasswordHasher`, `TokenService`) |

Example flow for tenant registration:

```
RegisterTenantHandler
  → create tenant aggregate
  → create owner membership
  → save via repositories
  → publish domain events
  → issue JWT
```

Commands follow **CQRS**: commands mutate state; queries read through repositories only.

### Domain layer (`backend/src/domain/`)

The core of the system. No Mongo documents or framework imports.

| Area | Contents |
|------|----------|
| `entities/` | `User`, `Tenant`, `Membership`, `Invite`, `Role` |
| `events/` | `UserRegistered`, `TenantCreated`, `InviteCreated`, `RoleChanged`, … |
| `repositories/` | Interfaces (`TenantRepository`, `UserRepository`, …) |
| `value_objects/` | `Email`, `Phone`, and other typed values |

Repository interfaces define contracts (`save`, `find_by_id`, `find_by_email`) without knowing about MongoDB.

### Infrastructure layer (`backend/src/infrastructure/`)

Technology-specific implementations.

| Area | Contents |
|------|----------|
| `persistence/mongo/documents/` | Beanie documents (`TenantDocument`, …) |
| `persistence/mongo/mappers/` | Document ↔ entity conversion |
| `persistence/mongo/` | Repository implementations, Unit of Work |
| `security/` | JWT token service, password hasher, rate limiting |
| `messaging/` | In-process and Redis Streams event publishers, transactional outbox relay |

Persistence models (`TenantDocument`) are separate from domain entities (`Tenant`). Mappers keep business logic out of the database layer.

### Request flow example

Registering a new tenant:

```
HTTP POST /tenants/register
        │
        ▼
API router
        │
        ▼
RegisterTenantHandler
        │
        ▼
Tenant + Membership aggregates
        │
        ▼
Repository interface
        │
        ▼
Mongo repository → MongoDB
```

When domain events are raised:

```
Tenant aggregate
        │
        ▼
TenantCreated event
        │
        ▼
Outbox / publisher
        │
        ▼
Redis Stream (production) or in-process handler (dev)
```

Each layer talks only to its immediate neighbour.

### DDD characteristics

- **Bounded context**: identity concepts only; no foreign domain leakage.
- **Ubiquitous language**: operations expressed as Tenant, Membership, Invite—not as Mongo collections or HTTP routes.
- **Domain events**: business facts (`TenantCreated`), not infrastructure signals (`MongoSaved`).
- **Dependency inversion**: application depends on ports; infrastructure implements them.

Further reading: [ADR-003: Hexagonal Architecture](docs/architecture/adr/003-hexagonal-architecture.md)

## Documentation

| Document | Description |
|----------|-------------|
| [`CUSTOMIZATION.md`](docs/architecture/CUSTOMIZATION.md) | How to adapt the service for other projects (layer-by-layer) |
| [`IDENTITY_CONTRACT.md`](docs/architecture/IDENTITY_CONTRACT.md) | JWT claims, endpoints, authorization model |
| [`EVENT_CONTRACT.md`](docs/architecture/EVENT_CONTRACT.md) | Domain event payloads and transport |
| [`DATA_SCHEMA.md`](docs/architecture/DATA_SCHEMA.md) | MongoDB collections and indexes |
| [`adr/002-identity-boundary-and-repo-extraction.md`](docs/architecture/adr/002-identity-boundary-and-repo-extraction.md) | Service boundary decision |
| [`adr/003-hexagonal-architecture.md`](docs/architecture/adr/003-hexagonal-architecture.md) | Layering and ports/adapters |
| [`adr/004-shared-permissions-kernel.md`](docs/architecture/adr/004-shared-permissions-kernel.md) | Shared permission constants |

## Roadmap

Current architecture foundations are in place. Planned maturity improvements:

- Expand aggregate behaviour and invariants in the domain layer
- Continue refining Unit of Work and transactional outbox usage
- Reduce responsibilities of `AuthApplicationService` as use cases grow
