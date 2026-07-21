# Identity Event Contract (Redis Streams)

Cross-service integration for the Pacific Identity Platform. Tracking and other consumers subscribe to the Identity event stream to build local projections.

## Transport

| Setting | Default | Description |
|---------|---------|-------------|
| `EVENT_TRANSPORT` | `in_process` | `in_process` or `redis_streams` |
| `REDIS_URL` | — | Required when `EVENT_TRANSPORT=redis_streams` |
| `IDENTITY_EVENT_STREAM` | `identity:events` | Redis Stream key |

## Stream format

Each message is an `XADD` entry with string fields from `DomainEvent.to_dict()`:

```json
{
  "type": "UserRegistered",
  "occurred_at": "2026-07-21T15:30:00+08:00",
  "user_id": "01H...",
  "email": "user@example.com",
  "tenant_id": "01H..."
}
```

Nested values (e.g. `role_ids` arrays) are JSON-encoded strings in Redis.

## Event catalog

| Event | Fields | When emitted |
|-------|--------|--------------|
| `TenantCreated` | `tenant_id`, `name`, `slug` | Default tenant bootstrap or self-serve signup |
| `TenantSuspended` | `tenant_id`, `reason?` | Admin suspends tenant |
| `UserRegistered` | `user_id`, `email`, `tenant_id` | New account after invite accept or registration |
| `UserAddedToTenant` | `tenant_id`, `user_id`, `role` | Membership created or restored |
| `InviteCreated` | `invite_id`, `tenant_id`, `email` | Admin creates invite |
| `InviteAccepted` | `invite_id`, `tenant_id`, `user_id` | Invitee completes signup |
| `RoleChanged` | `tenant_id`, `user_id`, `role_ids` | Membership role assignment changes |

## Consumer guidelines

1. Use consumer groups (`XREADGROUP`) for at-least-once delivery.
2. Idempotency key: `(type, tenant_id, user_id, occurred_at)` or event-specific IDs.
3. Do **not** read `identity_db` from Tracking — project only from events + JWT.
4. On `TenantSuspended`, invalidate local permission caches for that tenant.
5. On `RoleChanged` or membership events, refresh projections keyed by `user_id` + `tenant_id`.

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
