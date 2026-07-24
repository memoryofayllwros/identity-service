# ADR-004: Shared Permission Catalog as Manual Shared Kernel

## Status

Accepted (interim)

## Context

The permission catalog (`tracking.*`, `identity.*`, …) must be consistent across
`pacific-identity-platform` and `pacific-equipment-tracking` so that JWTs issued by Identity
are correctly authorised by Tracking.

## Decision

Maintain `backend/src/shared/permissions.py` in each service as an identical copy — a
*shared kernel* in DDD terms. Each service owns its copy; changes require a coordinated
update to both services and a bump of `SHARED_KERNEL_VERSION`.

## Sync procedure

1. Edit `shared/permissions.py` in the originating service.
2. Update `SHARED_KERNEL_VERSION` to today's ISO date.
3. Copy the file verbatim to the other service and update its `SHARED_KERNEL_VERSION`.
4. Open PRs in both repos in the same sprint; merge together.

## Consequences

- Negative: Manual coordination; drift is possible if the procedure is skipped.
- Positive: No inter-repo runtime dependency; each service deploys independently.
- Positive: Application layer accesses the permission catalog only through `SharedKernelPort`, implemented by `infrastructure/shared_kernel.py`; `shared/permissions.py` remains the sync source of truth.
- Planned migration: Extract to a private `pacific-shared` Python package (Phase 2+).
  Trigger: when a third service needs the catalog, or when manual sync causes a defect.

## Related

- ADR-003: Hexagonal Architecture for Identity Service
