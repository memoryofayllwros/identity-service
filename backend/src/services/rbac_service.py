"""RBAC seed, permission resolution, and perm_ver bumps (Identity)."""

from __future__ import annotations

from src.models.membership_doc import MembershipDoc
from src.models.permission_doc import PermissionDoc
from src.models.role_doc import RoleDoc
from src.models.tenant_doc import TenantDoc
from src.models.enums import UserRole
from src.shared.permissions import (
    ALL_PERMISSIONS,
    PLATFORM_ROLE_TEMPLATES,
    ROLE_CODE_ADMIN,
    ROLE_CODE_OPERATIONS,
)


async def ensure_permission_catalog() -> None:
    existing = {p.code for p in await PermissionDoc.find_all().to_list()}
    for code in ALL_PERMISSIONS:
        if code in existing:
            continue
        await PermissionDoc(code=code, description=code.replace(".", " ")).insert()


async def ensure_platform_role_templates() -> dict[str, RoleDoc]:
    """Seed platform RoleDoc templates (tenant_id=None)."""
    await ensure_permission_catalog()
    by_code: dict[str, RoleDoc] = {}
    for code, perms in PLATFORM_ROLE_TEMPLATES.items():
        role = await RoleDoc.find_one(RoleDoc.tenant_id == None, RoleDoc.code == code)  # noqa: E711
        if role is None:
            role = RoleDoc(
                tenant_id=None,
                code=code,
                name=code.replace("_", " ").title(),
                permissions=list(perms),
                is_system=True,
            )
            await role.insert()
        else:
            # Keep templates in sync with catalog
            if list(role.permissions) != list(perms):
                await role.set({"permissions": list(perms)})
        by_code[code] = role
    return by_code


async def ensure_tenant_roles(tenant_id: str) -> dict[str, RoleDoc]:
    """Copy platform templates into tenant-scoped roles if missing."""
    templates = await ensure_platform_role_templates()
    by_code: dict[str, RoleDoc] = {}
    for code, template in templates.items():
        role = await RoleDoc.find_one(RoleDoc.tenant_id == tenant_id, RoleDoc.code == code)
        if role is None:
            role = RoleDoc(
                tenant_id=tenant_id,
                code=code,
                name=template.name,
                permissions=list(template.permissions),
                is_system=True,
            )
            await role.insert()
        by_code[code] = role
    return by_code


async def resolve_role_ids_for_legacy(role: UserRole, tenant_id: str) -> list[str]:
    roles = await ensure_tenant_roles(tenant_id)
    code = ROLE_CODE_ADMIN if role == UserRole.ADMIN else ROLE_CODE_OPERATIONS
    doc = roles.get(code)
    return [doc.role_id] if doc else []


async def permissions_for_role_ids(role_ids: list[str]) -> list[str]:
    if not role_ids:
        return []
    roles = await RoleDoc.find({"role_id": {"$in": role_ids}}).to_list()
    collected: set[str] = set()
    for role in roles:
        collected.update(role.permissions)
    return sorted(collected)


async def permissions_for_membership(membership: MembershipDoc) -> list[str]:
    role_ids = list(membership.role_ids)
    if not role_ids:
        role_ids = await resolve_role_ids_for_legacy(membership.role, membership.tenant_id)
        if role_ids:
            await membership.set({"role_ids": role_ids})
    return await permissions_for_role_ids(role_ids)


async def bump_tenant_perm_ver(tenant_id: str) -> int:
    tenant = await TenantDoc.find_one(TenantDoc.tenant_id == tenant_id)
    if tenant is None:
        return 1
    new_ver = int(tenant.perm_ver or 1) + 1
    await tenant.set({"perm_ver": new_ver})
    memberships = await MembershipDoc.find(MembershipDoc.tenant_id == tenant_id).to_list()
    for membership in memberships:
        await membership.set({"perm_ver": new_ver})
    return new_ver


async def membership_perm_ver(membership: MembershipDoc, tenant: TenantDoc | None = None) -> int:
    if tenant is not None:
        return max(int(membership.perm_ver or 1), int(tenant.perm_ver or 1))
    return int(membership.perm_ver or 1)
