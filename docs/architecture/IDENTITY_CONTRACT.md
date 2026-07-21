# Identity Contract (Phase 3)

Platform Core Identity Service owns authentication and authorization snapshots.
Capabilities (Tracking, …) verify JWT and resolve permissions by `perm_ver`.

## JWT access token claims (`ver: 2`)

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | `user_id` |
| `tenant_id` | string | Active tenant |
| `email` | string | User email |
| `role` | string | Legacy role label (`admin` \| `operations`) |
| `role_ids` | string[] | `RoleDoc.role_id` list |
| `perm_ver` | int | Permission snapshot version |
| `scopes` | string[] | Optional early dual-track (capped); prefer `perm_ver` |
| `ver` | int | Claim schema version (`2`) |
| `exp` | int | Expiry (unix) |

**Algorithm:** RS256. JWKS may include previous key during rotation (`JWT_PREVIOUS_PUBLIC_KEY`).

## Endpoints (Identity)

Frozen OpenAPI: [`identity-openapi.json`](./identity-openapi.json) (re-export after Phase 3 routes).

| Endpoint | Purpose |
|----------|---------|
| `POST /api/auth/login` | Issue access (+ refresh) |
| `POST /api/auth/refresh` | Refresh; re-read Membership + permissions |
| `GET /api/auth/me` | Principal + optional `permissions` |
| `GET /api/auth/me/permissions` | Permission snapshot for cache hydrate |
| `GET /api/auth/events` | Auth audit (tenant-scoped) |
| `GET /.well-known/jwks.json` | Public keys |
| `POST /api/tenants/register` | Self-serve tenant signup |
| `POST /api/tenants/me/invites` | Create invite |
| `POST /api/tenants/invites/accept` | Accept invite |
| `POST /api/tenants/{id}/suspend` | Suspend tenant |
| `GET /api/tenants/me/entitlements` | Plan + features |
| `POST /api/billing/webhook` | Billing/entitlements hook (provider later) |
| `GET /api/users/{id}` | Directory |
| `GET /api/health` | Liveness |

## Endpoints (Tracking)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/users/directory` | Attribution + Identity hydrate |
| Business `/api/*` | `require_permission("tracking.…")` |

## Authorization

```text
WRONG: if role == "admin"
RIGHT: if "tracking.booking.write" in permissions
```

Tracking resolves permissions via JWT `scopes` (early) or Identity snapshot cache keyed by `perm_ver`.

## Rules

1. Tracking never reads `identity_db` and never stores `password_hash`.
2. Tracking documents keep `tenant_id`; no `tenants` collection in tracking DB.
3. Cross-tenant resource access → **404**.
4. Gateway routes `/api/auth|tenants|users` → Identity (except `/api/users/directory`).
5. Customer ≠ Tenant (see CAPABILITY_MAP / PLATFORM_ONBOARDING).

## Error semantics

| Case | Status |
|------|--------|
| Missing / invalid token | 401 |
| Missing permission | 403 |
| Resource in another tenant | 404 |
| Suspended tenant | 403 |
