#!/usr/bin/env python3
"""Copy Identity collections from tracking DB into identity_db (Phase 2).

Idempotent: upserts by primary business id.

  cd backend && poetry run python scripts/migrate_identity_db.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from pymongo import AsyncMongoClient

from src.infrastructure.settings import get_settings

IDENTITY_COLLECTIONS = ("tenants", "users", "memberships")


async def main() -> None:
    settings = get_settings()
    client = AsyncMongoClient(settings.mongodb_uri)
    source = client[settings.database_name]
    target = client[settings.identity_database_name]
    try:
        print(f"Source DB: {settings.database_name}")
        print(f"Target DB: {settings.identity_database_name}")
        for name in IDENTITY_COLLECTIONS:
            docs = await source[name].find({}).to_list(length=None)
            if not docs:
                print(f"  {name}: 0 documents (skip)")
                continue
            # Upsert by natural key
            key_field = {
                "tenants": "tenant_id",
                "users": "user_id",
                "memberships": "membership_id",
            }[name]
            upserted = 0
            for doc in docs:
                doc.pop("_id", None)
                key = doc.get(key_field)
                if not key:
                    continue
                await target[name].replace_one({key_field: key}, doc, upsert=True)
                upserted += 1
            print(f"  {name}: upserted {upserted}")
        print("Identity DB migration complete.")
        print("Tracking service uses TRACKING_DATABASE_NAME / DATABASE_NAME without users/tenants/memberships.")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
