#!/usr/bin/env python3
"""Idempotent Identity migration: default tenant and memberships."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.domain.enums import UserRole
from src.infrastructure.database import close_database, init_database
from src.infrastructure.dependencies import ensure_default_tenant, ensure_membership
from src.infrastructure.dependencies import get_membership_repository, get_user_repository
from src.shared.constants import DEFAULT_TENANT_ID


async def ensure_memberships_for_users() -> int:
    await ensure_default_tenant()
    created = 0
    users = await get_user_repository().find_all()
    for user in users:
        before = await get_membership_repository().find_by_tenant_and_user(
            DEFAULT_TENANT_ID, user.id
        )
        await ensure_membership(
            tenant_id=DEFAULT_TENANT_ID,
            user_id=user.id,
            role=before.role if before else UserRole.OPERATIONS,
        )
        if before is None:
            created += 1
    return created


async def main() -> None:
    print("Initializing Beanie…")
    await init_database()
    try:
        tenant = await ensure_default_tenant()
        print(f"Default tenant: {tenant.id} ({tenant.name})")
        memberships_created = await ensure_memberships_for_users()
        print(f"Memberships created: {memberships_created}")
        print("Migration complete.")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
