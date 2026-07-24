"""Identity database index migrations (run before Beanie init)."""

from __future__ import annotations

from pymongo.asynchronous.database import AsyncDatabase


async def reconcile_stale_indexes(database: AsyncDatabase) -> None:
    """
    Reconcile legacy Mongo indexes and role rows before Beanie init.

    The old multi-tenant schema stored one role row per tenant (same ``code``
    repeated). The single-tenant schema requires a globally unique ``code``.
    """
    await _drop_stale_role_indexes(database)
    await _dedupe_roles_by_code(database)


async def _drop_stale_role_indexes(database: AsyncDatabase) -> None:
    roles = database["roles"]
    cursor = await roles.list_indexes()
    async for index_info in cursor:
        name = index_info.get("name")
        if not name or name == "_id_":
            continue

        key = index_info.get("key") or {}
        drop = False
        if name == "code_1":
            # Drop any existing code index so Beanie can recreate it as unique.
            drop = True
        elif "tenant_id" in key and "code" in key:
            drop = True

        if drop:
            try:
                await roles.drop_index(name)
            except Exception:
                # Index may have been dropped already during a partial startup.
                pass


async def _dedupe_roles_by_code(database: AsyncDatabase) -> None:
    roles = database["roles"]
    docs = await roles.find({}).to_list(length=None)
    grouped: dict[str, list[dict]] = {}
    for doc in docs:
        code = doc.get("code")
        if not code:
            continue
        grouped.setdefault(code, []).append(doc)

    for code, entries in grouped.items():
        if len(entries) <= 1:
            if entries[0].get("tenant_id") is not None:
                await roles.update_one(
                    {"role_id": entries[0]["role_id"]},
                    {"$unset": {"tenant_id": ""}},
                )
            continue

        def _rank(doc: dict) -> tuple[int, str]:
            # Prefer platform/global template (no tenant_id), then earliest role_id.
            tenant_rank = 0 if doc.get("tenant_id") in (None, "") else 1
            return (tenant_rank, str(doc.get("role_id", "")))

        entries.sort(key=_rank)
        keeper = entries[0]
        await roles.update_one(
            {"role_id": keeper["role_id"]},
            {"$unset": {"tenant_id": ""}, "$set": {"is_system": True}},
        )
        for duplicate in entries[1:]:
            await roles.delete_one({"role_id": duplicate["role_id"]})
