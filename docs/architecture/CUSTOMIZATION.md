# Customizing the Identity Service for Other Projects

Domain layer is the **core** of customization, but adapting this Identity Service for another project usually requires changes across **domain + application + at least one adapter layer**, and sometimes `shared/` and deployment configuration.

## When changing domain alone is enough

These changes can be made **almost entirely in domain**, as long as **use-case flows stay the same** (same register / admin-create / login flows, different rules):

- Adjust **business invariants** on existing entities (e.g. lockout thresholds, company suspend rules)
- Add **new behavior** to existing aggregates (e.g. `User.require_mfa()`)
- Add new **domain events** (e.g. `UserPasswordChanged`)
- Tighten **value object** validation (Email, Phone format)

Example: changing lockout rules belongs mainly in `User.record_failed_login()` (`backend/src/domain/entities/user.py`).

## What most customizations touch

| Customization | Domain | Application | API | Infrastructure | Other |
|---------------|--------|-------------|-----|----------------|-------|
| Change business rules (lockout, status machine) | ✅ | Sometimes | ❌ | ❌ | — |
| **New use case** (SSO login, external IdP) | ✅ | ✅ commands/services | ✅ new routes | ✅ new port impl | config |
| **New entity** (Organization, Team) | ✅ entity + repo interface | ✅ handler | ✅ schema/route | ✅ document + mapper | migrations |
| **Different permission model** | ✅ User/Role | ✅ AuthorizationService | ✅ auth dependencies | — | `shared/permissions.py` |
| **Different feature bundles** | Optional | Optional | company routes | — | `PLAN_FEATURES` |
| **Deployment only** (single tenant ID, JWT) | ❌ | ❌ | ❌ | ❌ | `.env` |

## Why domain alone is not enough

Hexagonal layers have distinct responsibilities:

```
API            → what HTTP capabilities are exposed
Application    → how a use case is orchestrated step by step
Domain         → whether something is allowed by business rules
Infrastructure → how persistence, JWT, and messaging are implemented
```

**Domain does not define whether a use case exists.**

Example: admin-create user flow

1. `api/identity_routers.py` — HTTP entry (`POST /api/users`)
2. `CreateUserHandler` — orchestration (validate, hash password, UoW, outbox)
3. `User.register()` — business rules + `UserRegistered` event
4. Mongo repository — persistence

Changing only `User.register()` does not add a new API or workflow. Adding only an API route without domain/application changes will not enforce correct business rules.

## Common reuse patterns in this project

### 1. Configuration only (minimal code changes)

- `TENANT_INSTANCE_ID`, JWT keys
- `PLAN_FEATURES` (bootstrap default company features)
- `shared/permissions.py` (different capability prefixes)

### 2. Domain + application (most common)

- New registration rules → `User.register()` + `AuthApplicationService.register()`
- New user provisioning rules → `CreateUserHandler`
- Company profile rules → `Tenant.update_profile()` + company API

### 3. Domain + application + infrastructure

- New aggregate → entity + repository interface + Mongo document/mapper
- New auth mechanism → `application/ports/` + `infrastructure/security/`

### 4. What not to change for project customization

- Outbound HTTP calls to sibling microservices (Identity is consumed, not an orchestrator)
- Framework or persistence imports inside domain (breaks architectural boundaries)

## Decision guide

| Question | Layer |
|----------|-------|
| Is this allowed by business rules? | **Domain** |
| What objects are involved and in what order? | **Application** |
| How do external clients invoke this? | **API** (+ `schemas/`) |
| How is it stored, signed, or published? | **Infrastructure** |
| What permission codes exist on this platform? | **`shared/permissions.py`** |

## Summary

**Domain is the core of customization, not the only entry point.**

- New rules → start in domain
- New capabilities or flows → domain + application + API (+ infrastructure when storage or technology changes)

## Related

- [ADR-002: Identity boundary and repo extraction](./adr/002-identity-boundary-and-repo-extraction.md)
- [ADR-003: Hexagonal Architecture](./adr/003-hexagonal-architecture.md)
- [DATA_SCHEMA.md](./DATA_SCHEMA.md)
- [IDENTITY_CONTRACT.md](./IDENTITY_CONTRACT.md)
- [README.md](../../README.md)
