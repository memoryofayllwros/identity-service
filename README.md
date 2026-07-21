# Pacific Identity Platform

IAM service for the Pacific equipment tracking tenant runtime.

**Owns:** User, Role, Permission, Invitation, Authentication, Authorization, JWT/JWKS, basic tenant metadata.

**Does NOT own:** Customer, Asset, Booking, Quotation, or any business entity. Legacy Tracking code has been removed from this repository; business domain logic belongs in `pacific-equipment-tracking`.

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

## Architecture

This repo uses **Service + Beanie ODM** for IAM entities (no Domain/Repository layer). Core business aggregates (Booking, Kit, Component, etc.) should use Domain + Repository separation in the Tracking service repository per ADR-002.
