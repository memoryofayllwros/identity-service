from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities.membership import Membership
from src.domain.entities.role import Role
from src.domain.entities.tenant import Tenant
from src.domain.enums import UserRole
from src.domain.id_generator import IDGenerator
from src.domain.repositories import (
    MembershipRepository,
    PermissionCatalogRepository,
    RoleRepository,
    TenantRepository,
)
from src.application.principal import Principal
from src.shared.permissions import (
    ALL_PERMISSIONS,
    PLATFORM_ROLE_TEMPLATES,
    ROLE_CODE_ADMIN,
    ROLE_CODE_OPERATIONS,
)


class AuthorizationError(Exception):
    pass


@dataclass
class AuthorizationService:
    role_repo: RoleRepository
    membership_repo: MembershipRepository
    tenant_repo: TenantRepository
    permission_catalog_repo: PermissionCatalogRepository
    id_gen: IDGenerator

    async def ensure_permission_catalog(self) -> None:
        await self.permission_catalog_repo.ensure_catalog(list(ALL_PERMISSIONS))

    async def ensure_platform_role_templates(self) -> dict[str, Role]:
        await self.ensure_permission_catalog()
        by_code: dict[str, Role] = {}
        for code, perms in PLATFORM_ROLE_TEMPLATES.items():
            role = await self.role_repo.find_platform_template(code)
            if role is None:
                role = Role(
                    id=self.id_gen(),
                    tenant_id=None,
                    code=code,
                    name=code.replace("_", " ").title(),
                    permissions=list(perms),
                    is_system=True,
                )
                await self.role_repo.save(role)
            elif list(role.permissions) != list(perms):
                role.permissions = list(perms)
                await self.role_repo.save(role)
            by_code[code] = role
        return by_code

    async def ensure_tenant_roles(self, tenant_id: str) -> dict[str, Role]:
        templates = await self.ensure_platform_role_templates()
        by_code: dict[str, Role] = {}
        for code, template in templates.items():
            role = await self.role_repo.find_tenant_role(tenant_id, code)
            if role is None:
                role = Role(
                    id=self.id_gen(),
                    tenant_id=tenant_id,
                    code=code,
                    name=template.name,
                    permissions=list(template.permissions),
                    is_system=True,
                )
                await self.role_repo.save(role)
            by_code[code] = role
        return by_code

    async def resolve_role_ids_for_legacy(self, role: UserRole, tenant_id: str) -> list[str]:
        roles = await self.ensure_tenant_roles(tenant_id)
        code = ROLE_CODE_ADMIN if role == UserRole.ADMIN else ROLE_CODE_OPERATIONS
        doc = roles.get(code)
        return [doc.id] if doc else []

    async def permissions_for_role_ids(self, role_ids: list[str]) -> list[str]:
        if not role_ids:
            return []
        roles = await self.role_repo.find_by_ids(role_ids)
        collected: set[str] = set()
        for role in roles:
            collected.update(role.permissions)
        return sorted(collected)

    async def permissions_for_membership(self, membership: Membership) -> list[str]:
        role_ids = list(membership.role_ids)
        if not role_ids:
            role_ids = await self.resolve_role_ids_for_legacy(membership.role, membership.tenant_id)
            if role_ids:
                membership.assign_roles(role_ids)
                await self.membership_repo.save(membership)
        return await self.permissions_for_role_ids(role_ids)

    async def membership_perm_ver(
        self, membership: Membership, tenant: Tenant | None = None
    ) -> int:
        if tenant is not None:
            return max(int(membership.perm_ver or 1), int(tenant.perm_ver or 1))
        return int(membership.perm_ver or 1)

    async def bump_tenant_perm_ver(self, tenant_id: str) -> int:
        tenant = await self.tenant_repo.find_by_id(tenant_id)
        if tenant is None:
            return 1
        new_ver = tenant.bump_perm_ver()
        await self.tenant_repo.save(tenant)
        await self.membership_repo.sync_perm_ver_for_tenant(tenant_id, new_ver)
        return new_ver

    def check_permission(self, principal: Principal, *codes: str) -> None:
        if not codes:
            return
        if any(principal.has_permission(code) for code in codes):
            return
        raise AuthorizationError("Forbidden.")
