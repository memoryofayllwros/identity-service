#!/usr/bin/env python3
"""Seed RBAC catalog + backfill membership role_ids / tenant perm_ver (Phase 3)."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SERVICE_NAME", "identity")

from src.infrastructure.database import close_database, init_database
from src.infrastructure.dependencies import get_authorization_service
from src.infrastructure.settings import get_settings
from src.models.membership_doc import MembershipDoc
from src.models.tenant_doc import TenantDoc
from src.shared.permissions import PLAN_FEATURES


async def main() -> None:
    get_settings.cache_clear()
    await init_database()
    authz = get_authorization_service()
    await authz.ensure_platform_role_templates()

    tenants = await TenantDoc.find_all().to_list()
    for tenant in tenants:
        updates: dict = {}
        if not getattr(tenant, "status", None):
            updates["status"] = "active" if tenant.is_active else "suspended"
        if not getattr(tenant, "features", None):
            updates["features"] = list(PLAN_FEATURES.get(tenant.plan, PLAN_FEATURES["starter"]))
        if getattr(tenant, "perm_ver", None) is None:
            updates["perm_ver"] = 1
        if updates:
            await tenant.set(updates)
        await authz.ensure_tenant_roles(tenant.tenant_id)

    memberships = await MembershipDoc.find_all().to_list()
    for m in memberships:
        role_ids = list(m.role_ids or [])
        if not role_ids:
            role_ids = await authz.resolve_role_ids_for_legacy(m.role, m.tenant_id)
        tenant = await TenantDoc.find_one(TenantDoc.tenant_id == m.tenant_id)
        perm_ver = int(tenant.perm_ver or 1) if tenant else 1
        await m.set({"role_ids": role_ids, "perm_ver": perm_ver})

    print(f"RBAC seed complete: tenants={len(tenants)} memberships={len(memberships)}")
    await close_database()


if __name__ == "__main__":
    asyncio.run(main())
