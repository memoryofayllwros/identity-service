# Identity Event Contract (Redis Streams)

Cross-service integration for the Pacific Identity Platform. Tracking and other consumers subscribe to the Identity event stream to build local projections.

## Transport

| Setting | Default | Description |
|---------|---------|-------------|
| `EVENT_TRANSPORT` | `in_process` | `in_process` or `redis_streams` |
| `REDIS_URL` | — | Required when `EVENT_TRANSPORT=redis_streams` |
| `IDENTITY_EVENT_STREAM` | `identity:events` | Redis Stream key |

Domain events are written to the `outbox` collection inside the same transaction as aggregate persistence, then relayed to Redis by `OutboxRelayWorker`.

## Stream format

Each message is an `XADD` entry with string fields from `DomainEvent.to_dict()`:

```json
{
  "type": "UserRegistered",
  "occurred_at": "2026-07-21T15:30:00+08:00",
  "user_id": "01H...",
  "mobile": "+85291234567"
}
```

Nested values (e.g. arrays) are JSON-encoded strings in Redis when required by the publisher adapter.

## Event catalog

### Currently emitted (single-tenant schema)

| Event | Fields | When emitted |
|-------|--------|--------------|
| `UserRegistered` | `user_id`, `mobile` (E.164) | Admin creates user via `CreateUserHandler` (UoW + outbox) |
| `UserDeactivated` | `user_id` | User aggregate deactivated (UoW + outbox) |
| `TenantCreated` | `tenant_id`, `name`, `slug` | Defined on `Tenant.create()`; emitted only when persisted through a UoW path |

> **Note:** Bootstrap registration (`POST /api/auth/register`) and default company seeding save directly without outbox today. Consumers should not rely on those paths producing stream events until wired through UoW.

### Auth audit events (MongoDB only)

These are stored in `auth_events` and are **not** published to Redis Streams:

| `event_type` | Description |
|--------------|-------------|
| `user.registered` | Bootstrap admin registered |
| `auth.login` | Successful login |
| `auth.login_failed` | Failed login |
| `auth.password_changed` | Password changed |

### Removed (legacy multi-tenant schema)

These event types remain in `domain/events/` for reference but are **no longer emitted**:

| Event | Reason removed |
|-------|----------------|
| `UserAddedToTenant` | No membership model |
| `InviteCreated` / `InviteAccepted` | Replaced by admin-create flow |
| `RoleChanged` | Permissions updated in-place on user row |
| `TenantSuspended` | Company suspend not exposed via API yet |

## Consumer guidelines

1. Use consumer groups (`XREADGROUP`) for at-least-once delivery.
2. Idempotency key: `(type, user_id, occurred_at)` or event-specific IDs (`user_id` for `UserRegistered`).
3. Do **not** read `identity_db` from Tracking — project only from events + JWT.
4. On `UserDeactivated`, invalidate local caches keyed by `user_id`.
5. JWT still carries `tenant_id=DEFAULT_TENANT_ID` for downstream compatibility; there is no tenant switching.

## Example consumer (pseudo)

```python
messages = await redis.xreadgroup(
    groupname="tracking",
    consumername="worker-1",
    streams={"identity:events": ">"},
    count=10,
)
for _stream, entries in messages:
    for entry_id, fields in entries:
        event_type = fields["type"]
        if event_type == "UserRegistered":
            await upsert_tracking_user_view(fields)
        await redis.xack("identity:events", "tracking", entry_id)
```

## In-process fallback

When `EVENT_TRANSPORT=in_process`, events are dispatched only within the Identity process (tests, local dev). Cross-service sync requires Redis Streams or future webhook support.
