from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import UserDTO, user_to_dto
from src.application.services.authorization_service import AuthorizationService
from src.application.services.membership_service import MembershipService
from src.domain.entities.membership import Membership
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.exceptions import MembershipInactive, TenantNotFound, TenantSuspended, UserNotFound
from src.domain.repositories import MembershipRepository, TenantRepository, UserRepository


async def _active_membership(
    *,
    user: User,
    tenant_repo: TenantRepository,
    membership_repo: MembershipRepository,
    tenant_instance_id: str,
) -> tuple[Membership, Tenant]:
    tenant = await tenant_repo.find_by_id(tenant_instance_id)
    if tenant is None:
        raise TenantNotFound()

    membership = await membership_repo.find_active_by_user(user.id)
    if membership is None:
        raise MembershipInactive()

    tenant_doc = await tenant_repo.find_by_id(membership.tenant_id)
    if tenant_doc is None:
        tenant_doc = tenant
    if tenant_doc.is_suspended:
        raise TenantSuspended()
    return membership, tenant_doc


@dataclass(frozen=True)
class GetUserQuery:
    user_id: str
    user: User | None = None


@dataclass
class GetUserHandler:
    user_repo: UserRepository
    membership_repo: MembershipRepository
    tenant_repo: TenantRepository
    authz: AuthorizationService
    membership_service: MembershipService
    tenant_instance_id: str

    async def execute(self, query: GetUserQuery) -> UserDTO:
        user = query.user or await self.user_repo.find_by_id(query.user_id)
        if user is None:
            raise UserNotFound()
        membership, tenant = await _active_membership(
            user=user,
            tenant_repo=self.tenant_repo,
            membership_repo=self.membership_repo,
            tenant_instance_id=self.tenant_instance_id,
        )
        perms = await self.authz.permissions_for_membership(membership)
        return user_to_dto(
            user,
            tenant_id=membership.tenant_id,
            tenant_name=tenant.name,
            role=membership.role,
            permissions=list(perms),
            perm_ver=await self.authz.membership_perm_ver(membership, tenant),
        )


@dataclass(frozen=True)
class ListUsersQuery:
    tenant_id: str | None = None


@dataclass
class ListUsersHandler:
    user_repo: UserRepository
    membership_repo: MembershipRepository
    tenant_repo: TenantRepository
    authz: AuthorizationService
    membership_service: MembershipService
    tenant_instance_id: str

    async def execute(self, query: ListUsersQuery) -> list[UserDTO]:
        tenant = await self.tenant_repo.find_by_id(self.tenant_instance_id)
        if tenant is None:
            raise TenantNotFound()

        users = await self.user_repo.find_all()
        results: list[UserDTO] = []
        for user in users:
            membership = await self.membership_repo.find_by_tenant_and_user(tenant.id, user.id)
            role = membership.role if membership else UserRole.OPERATIONS
            results.append(
                user_to_dto(user, tenant_id=tenant.id, tenant_name=tenant.name, role=role)
            )
        return results


@dataclass(frozen=True)
class GetMyPermissionsQuery:
    user_id: str
    user: User | None = None


@dataclass
class GetMyPermissionsHandler:
    user_repo: UserRepository
    membership_repo: MembershipRepository
    tenant_repo: TenantRepository
    authz: AuthorizationService
    membership_service: MembershipService
    tenant_instance_id: str

    async def execute(self, query: GetMyPermissionsQuery) -> dict:
        user = query.user or await self.user_repo.find_by_id(query.user_id)
        if user is None:
            raise UserNotFound()
        membership, tenant = await _active_membership(
            user=user,
            tenant_repo=self.tenant_repo,
            membership_repo=self.membership_repo,
            tenant_instance_id=self.tenant_instance_id,
        )
        perms = await self.authz.permissions_for_membership(membership)
        return {
            "user_id": user.id,
            "tenant_id": membership.tenant_id,
            "role_ids": list(membership.role_ids),
            "perm_ver": await self.authz.membership_perm_ver(membership, tenant),
            "permissions": list(perms),
        }
