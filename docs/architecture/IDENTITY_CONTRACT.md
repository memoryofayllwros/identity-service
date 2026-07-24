# Identity Contract (Single-Tenant)

Platform Core Identity Service owns authentication and authorization for **one company per deployment**. Capabilities (Tracking, …) verify JWT and resolve permissions from token claims or Identity API.

## JWT access token claims (`ver: 2`)

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | `user_id` |
| `tenant_id` | string | Fixed deployment ID (`DEFAULT_TENANT_ID` / `TENANT_INSTANCE_ID`) |
| `email` | string | User email |
| `role` | string | Inferred label (`admin` \| `operations`) |
| `role_ids` | string[] | Empty in single-tenant schema (legacy claim retained) |
| `perm_ver` | int | Fixed at `1` (no membership snapshot versioning) |
| `scopes` | string[] | Permission codes (capped at 32 on issue) |
| `ver` | int | Claim schema version (`2`) |
| `exp` | int | Expiry (unix) |

**Algorithm:** RS256. JWKS may include previous key during rotation (`JWT_PREVIOUS_PUBLIC_KEY`).

## Endpoints (Identity)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/auth/register` | Bootstrap first admin (only when no users exist) |
| `POST /api/auth/login` | Issue access (+ refresh) token |
| `POST /api/auth/refresh` | Refresh; re-read user permissions |
| `POST /api/auth/change-password` | Change password; clears `must_change_password` |
| `POST /api/auth/forgot-password` | Password reset stub |
| `GET /api/auth/me` | Current user profile |
| `GET /api/auth/me/permissions` | Permission snapshot |
| `PATCH /api/auth/me` | Update own profile |
| `GET /api/auth/events` | Auth audit log |
| `GET /api/auth/users` | User list (legacy route on auth router) |
| `GET /api/users` | Paginated user directory (admin) |
| `POST /api/users` | Admin-create user with temp password |
| `GET /api/users/{id}` | User detail |
| `PATCH /api/users/{id}` | Update user (status, role, profile) |
| `GET /api/users/by-ids` | Bulk directory hydrate |
| `GET /api/company` | Company profile |
| `PATCH /api/company` | Update company name / features |
| `GET /.well-known/jwks.json` | Public keys |
| `GET /api/health` | Liveness |

**Removed (legacy multi-tenant schema)**

| Endpoint | Replacement |
|----------|-------------|
| `POST /api/tenants/register` | Fixed `TENANT_INSTANCE_ID`; company seeded at startup |
| `POST /api/tenants/me/invites` | `POST /api/users` (admin-create) |
| `POST /api/tenants/invites/accept` | Admin sets password; user changes via `/api/auth/change-password` |
| `POST /api/tenants/{id}/suspend` | Not exposed yet |
| `GET /api/tenants/me/entitlements` | `GET /api/company` (`features` field) |

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

Tracking resolves permissions via JWT `scopes` or Identity snapshot cache. There is no per-tenant membership lookup.

## Rules

1. Tracking never reads `identity_db` and never stores `password_hash`.
2. Tracking documents may keep `tenant_id` for row scoping; no `tenants` collection in tracking DB.
3. This deployment serves one company — no tenant switching APIs.
4. Gateway routes `/api/auth|users|company` → Identity (except `/api/users/directory` on Tracking).
5. Customer ≠ Tenant (see CAPABILITY_MAP / PLATFORM_ONBOARDING).

## Error semantics

| Case | Status |
|------|--------|
| Missing / invalid token | 401 |
| Missing permission | 403 |
| User suspended / deactivated | 401 |
| Suspended company | 403 |
| Registration when users already exist | 403 |
