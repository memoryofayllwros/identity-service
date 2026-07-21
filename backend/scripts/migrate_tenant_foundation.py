#!/usr/bin/env python3
"""Idempotent Identity migration: default tenant and memberships.

Usage:

  cd backend && poetry run python scripts/migrate_tenant_foundation.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.infrastructure.database import close_database, init_database
from src.models.membership_doc import MembershipDoc
from src.models.user_doc import UserDoc
from src.services.auth_service import ensure_default_tenant, ensure_membership
from src.shared.constants import DEFAULT_TENANT_ID


async def ensure_memberships_for_users() -> int:
    await ensure_default_tenant()
    created = 0
    users = await UserDoc.find_all().to_list()
    for user in users:
        before = await MembershipDoc.find_one(
            MembershipDoc.tenant_id == DEFAULT_TENANT_ID,
            MembershipDoc.user_id == user.user_id,
        )
        await ensure_membership(
            tenant_id=DEFAULT_TENANT_ID,
            user_id=user.user_id,
            role=user.role,
        )
        if before is None:
            created += 1
    return created


async def main() -> None:
    print("Initializing Beanie…")
    await init_database()
    try:
        tenant = await ensure_default_tenant()
        print(f"Default tenant: {tenant.tenant_id} ({tenant.name})")
        memberships_created = await ensure_memberships_for_users()
        print(f"Memberships created: {memberships_created}")
        print("Migration complete.")
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
