#!/usr/bin/env python3
"""Remove legacy UserDoc.role field from existing MongoDB user documents."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SERVICE_NAME", "identity")

from src.infrastructure.database import close_database, init_database
from src.infrastructure.settings import get_settings
from src.models.user_doc import UserDoc


async def main() -> None:
    get_settings.cache_clear()
    await init_database()
    users = await UserDoc.find_all().to_list()
    updated = 0
    for user in users:
        raw = user.model_dump()
        if "role" in raw:
            await user.set({"role": None})
            await UserDoc.get_motor_collection().update_one(
                {"user_id": user.user_id},
                {"$unset": {"role": ""}},
            )
            updated += 1
    print(f"Unset role on {updated} user documents (scanned {len(users)}).")
    await close_database()


if __name__ == "__main__":
    asyncio.run(main())
