# Pacific Identity Platform

IAM service for the Pacific equipment tracking tenant runtime.

**Owns:** User, Role, Permission, Invitation, Authentication, Authorization, JWT/JWKS, basic tenant metadata.

**Does NOT own:** Customer, Asset, Booking, Quotation, or any business entity. Business domain logic belongs in `pacific-equipment-tracking`.

## Run locally

```bash
cd backend
poetry install
SERVICE_NAME=identity uvicorn src.main:app --reload --port 8001
```

## Environment

Copy `deployment/.env.example` to `deployment/.env` and set:

- `MONGODB_URI`
- `IDENTITY_DATABASE_NAME=identity_db`
- `TENANT_INSTANCE_ID` — immutable tenant for this deployment
- `DEPLOYMENT_ID`
- `SECRET_KEY`, `REFRESH_SECRET_KEY`, JWT PEM keys
- `EVENT_TRANSPORT` — `in_process` (default) or `redis_streams`
- `REDIS_URL` — required when using Redis Streams

## Architecture

Hexagonal Architecture (ADR-003):

- **Domain** — entities, value objects, events, repository ports (`backend/src/domain/`)
- **Application** — command/query handlers (`backend/src/application/`)
- **Infrastructure** — Mongo persistence adapters, JWT, Redis Streams (`backend/src/infrastructure/`)

Persistence models: `infrastructure/persistence/mongo/documents/`. See [DATA_SCHEMA.md](docs/architecture/DATA_SCHEMA.md) and [EVENT_CONTRACT.md](docs/architecture/EVENT_CONTRACT.md).
