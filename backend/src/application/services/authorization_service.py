from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities.role import Role
from src.domain.entities.user import User
from src.domain.id_generator import IDGenerator
from src.domain.repositories import RoleRepository
from src.application.ports.shared_kernel import SharedKernelPort
from src.application.principal import Principal
from src.shared.permissions import IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN


class AuthorizationError(Exception):
    pass


@dataclass
class AuthorizationService:
    role_repo: RoleRepository
    shared_kernel: SharedKernelPort
    id_gen: IDGenerator

    async def ensure_system_roles(self) -> dict[str, Role]:
        by_code: dict[str, Role] = {}
        for code, perms in self.shared_kernel.platform_role_templates().items():
            role = await self.role_repo.find_by_code(code)
            if role is None:
                role = Role(
                    id=self.id_gen(),
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

    async def permissions_for_role_code(self, role_code: str) -> list[str]:
        role = await self.role_repo.find_by_code(role_code)
        if role is None:
            return []
        return sorted(role.permissions)

    def permissions_for_user(self, user: User) -> list[str]:
        return sorted(user.permissions)

    def check_permission(self, principal: Principal, *codes: str) -> None:
        if not codes:
            return
        if any(principal.has_permission(code) for code in codes):
            return
        raise AuthorizationError("Forbidden.")

    def check_user_admin_permission(self, principal: Principal) -> None:
        self.check_permission(
            principal,
            self.shared_kernel.identity_tenant_admin,
            self.shared_kernel.identity_user_admin,
        )

    def infer_role_from_permissions(self, permissions: list[str]) -> str:
        admin_markers = {IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN}
        if admin_markers.intersection(permissions):
            return self.shared_kernel.role_code_admin
        return self.shared_kernel.role_code_operations
