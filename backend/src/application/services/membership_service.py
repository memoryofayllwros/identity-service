from __future__ import annotations

from dataclasses import dataclass

from src.application.services.authorization_service import AuthorizationService
from src.domain.entities._base import AggregateRoot
from src.domain.entities.membership import Membership
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.enums import UserRole
from src.domain.repositories import MembershipRepository, OutboxRepository, TenantRepository
from src.domain.id_generator import IDGenerator
from src.domain.unit_of_work import UnitOfWork
from src.domain.utils import now_hk


@dataclass
class MembershipService:
    membership_repo: MembershipRepository
    tenant_repo: TenantRepository
    authz: AuthorizationService
    outbox_repo: OutboxRepository
    id_gen: IDGenerator

    async def find_active_for_user(self, user_id: str) -> Membership | None:
        return await self.membership_repo.find_active_by_user(user_id)

    async def find_for_tenant_and_user(
        self, tenant_id: str, user_id: str
    ) -> Membership | None:
        return await self.membership_repo.find_by_tenant_and_user(tenant_id, user_id)

    async def _persist_events(self, aggregate: AggregateRoot) -> None:
        for event in aggregate.collect_events():
            await self.outbox_repo.save(
                OutboxRecord(
                    id=self.id_gen(),
                    event_type=event.event_type,
                    payload=event.to_dict(),
                    created_at=now_hk(),
                )
            )

    async def ensure_membership(
        self,
        *,
        tenant_id: str,
        user_id: str,
        role: UserRole,
        uow: UnitOfWork | None = None,
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
                if uow is not None:
                    uow.register(existing)
                else:
                    await self.membership_repo.save(existing)
                    await self._persist_events(existing)
                    await self.authz.bump_tenant_perm_ver(tenant_id)
                refreshed = await self.membership_repo.find_by_tenant_and_user(
                    tenant_id, user_id
                )
                return refreshed or existing
            return existing

        membership = Membership.create(
            membership_id=self.id_gen(),
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            role_ids=role_ids,
            perm_ver=perm_ver,
        )
        if uow is not None:
            uow.register(membership)
            return membership

        await self.membership_repo.save(membership)
        await self._persist_events(membership)
        return membership
