from __future__ import annotations

from dataclasses import dataclass

from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.membership import Membership
from src.domain.enums import UserRole
from src.domain.events import RoleChanged, UserAddedToTenant
from src.domain.repositories import MembershipRepository, TenantRepository
from src.domain.events.publisher import EventPublisher
from src.domain.id_generator import IDGenerator


@dataclass
class MembershipService:
    membership_repo: MembershipRepository
    tenant_repo: TenantRepository
    authz: AuthorizationService
    publisher: EventPublisher
    id_gen: IDGenerator

    async def find_active_for_user(self, user_id: str) -> Membership | None:
        return await self.membership_repo.find_active_by_user(user_id)

    async def find_for_tenant_and_user(
        self, tenant_id: str, user_id: str
    ) -> Membership | None:
        return await self.membership_repo.find_by_tenant_and_user(tenant_id, user_id)

    async def ensure_membership(
        self,
        *,
        tenant_id: str,
        user_id: str,
        role: UserRole,
    ) -> Membership:
        await self.authz.ensure_tenant_roles(tenant_id)
        role_ids = await self.authz.resolve_role_ids_for_legacy(role, tenant_id)
        tenant = await self.tenant_repo.find_by_id(tenant_id)
        perm_ver = int(tenant.perm_ver or 1) if tenant else 1

        existing = await self.membership_repo.find_by_tenant_and_user(tenant_id, user_id)
        if existing is not None:
            changed = False
            if existing.role != role or not existing.is_active:
                existing.activate(role)
                changed = True
            if list(existing.role_ids) != role_ids:
                existing.assign_roles(role_ids, role)
                changed = True
            if existing.perm_ver != perm_ver:
                existing.sync_perm_ver(perm_ver)
                changed = True
            if changed:
                await self.membership_repo.save(existing)
                await self.authz.bump_tenant_perm_ver(tenant_id)
                refreshed = await self.membership_repo.find_by_tenant_and_user(tenant_id, user_id)
                return refreshed or existing
            return existing

        membership = Membership(
            id=self.id_gen(),
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            role_ids=role_ids,
            perm_ver=perm_ver,
        )
        await self.membership_repo.save(membership)
        await self.publisher.publish(
            UserAddedToTenant(tenant_id=tenant_id, user_id=user_id, role=role.value)
        )
        await self.publisher.publish(
            RoleChanged(tenant_id=tenant_id, user_id=user_id, role_ids=tuple(role_ids))
        )
        return membership
