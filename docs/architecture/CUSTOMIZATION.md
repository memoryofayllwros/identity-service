# Customizing the Identity Service for Other Projects

Domain layer is the **core** of customization, but adapting this Identity Service for another project usually requires changes across **domain + application + at least one adapter layer**, and sometimes `shared/` and deployment configuration.

## When changing domain alone is enough

These changes can be made **almost entirely in domain**, as long as **use-case flows stay the same** (same register / invite / login flows, different rules):

- Adjust **business invariants** on existing entities (e.g. invite expiry days, tenant suspend rules)
- Add **new behavior** to existing aggregates (e.g. `Tenant.change_plan()`)
- Add new **domain events** (e.g. `TenantPlanChanged`)
- Tighten **value object** validation (Email, Phone format)

Example: changing invite expiry logic belongs mainly in `Invite.accept()` and `Invite.create()` (`backend/src/domain/entities/invite.py`).

## What most customizations touch

| Customization | Domain | Application | API | Infrastructure | Other |
|---------------|--------|-------------|-----|----------------|-------|
| Change business rules (expiry, state machine) | ✅ | Sometimes | ❌ | ❌ | — |
| **New use case** (SSO login, multi-tenant switch) | ✅ | ✅ commands/services | ✅ new routes | ✅ new port impl | config |
| **New entity** (Organization, Team) | ✅ entity + repo interface | ✅ handler | ✅ schema/route | ✅ document + mapper | migrations |
| **Different permission model** | ✅ Role/Membership | ✅ AuthorizationService | ✅ auth dependencies | — | `shared/permissions.py` |
| **Different plan/feature bundles** | Optional | Optional | entitlements routes | — | `PLAN_FEATURES` |
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

Example: accept invite flow

1. `api/tenants.py` — HTTP entry
2. `AcceptInviteHandler` — orchestration (load data, transaction, audit)
3. `Invite.accept()` — business rules
4. Mongo repository — persistence

Changing only `Invite.accept()` does not add a new API or workflow. Adding only an API route without domain/application changes will not enforce correct business rules.

## Common reuse patterns in this project

### 1. Configuration only (minimal code changes)

- `TENANT_INSTANCE_ID`, JWT keys
- `PLAN_FEATURES` (different SaaS tiers)
- `shared/permissions.py` (different capability prefixes)

### 2. Domain + application (most common)

- New registration rules → `User.register()` + `AuthApplicationService.register()`
- New tenant lifecycle → `Tenant` entity + `SuspendTenantHandler`, etc.

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
- [IDENTITY_CONTRACT.md](./IDENTITY_CONTRACT.md)
- [README.md](../../README.md)
