# ADR-002: Identity boundary and repository extraction

## Status

Accepted (Phase 1)

## Context

Identity and Tracking previously shared one backend repository with dual entrypoints (`identity_main.py` and `main.py`). This blurred service ownership and risked Identity becoming a "God Service" that accumulates business data.

## Decision

1. **Extract Identity** into `pacific-identity-platform` — a dedicated repository and Docker image.
2. **Keep Tracking** in `pacific-equipment-tracking` — business data only.
3. **Identity owns IAM only:** User, Role, Permission, Invitation, Authentication, Authorization, JWT/JWKS, and minimal tenant metadata (display name, logo, locale for login UI).
4. **Identity does NOT own:** Customer, Asset, Booking, Quotation, or any business entity.
5. **Business services** consult Identity only via HTTP for JWKS, directory, and permission snapshots.
6. **Phase 1:** no cross-service webhook/event sync; API-only integration.
7. **Single-tenant binding:** each deployment has immutable `TENANT_INSTANCE_ID`; no tenant signup or switching APIs.

## ADR statements

> The Identity service owns identities, authentication, authorization, and access-control metadata. It does not own business entities or tenant business data.

> Business services own their domain data and consult the Identity service only for identity, directory, and authorization information.

## Consequences

- Positive: Clear repo and runtime boundaries; Identity cannot grow into a tenant business database.
- Positive: Independent deploy, test, and migrate cycles per service.
- Negative: Two repositories to clone and coordinate in Compose/Ansible.
- Negative: Shared JWT key material must be provisioned consistently across tenant stack.

## Related

- ADR-001: Identity / Tracking split (modular monolith precursor)
- `docs/architecture/IDENTITY_CONTRACT.md`
