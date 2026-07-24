from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import UserDTO, user_to_dto
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.user import User
from src.domain.enums import UserRole, UserStatus
from src.domain.exceptions import UserInactive, UserNotFound
from src.domain.repositories import UserRepository
from src.shared.permissions import IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN


def _resolve_role(user: User) -> UserRole:
    admin_markers = {IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN}
    if admin_markers.intersection(user.permissions):
        return UserRole.ADMIN
    return UserRole.OPERATIONS


@dataclass(frozen=True)
class GetUserQuery:
    user_id: str
    user: User | None = None


@dataclass
class GetUserHandler:
    user_repo: UserRepository
    authz: AuthorizationService

    async def execute(self, query: GetUserQuery) -> UserDTO:
        user = query.user or await self.user_repo.find_by_id(query.user_id)
        if user is None:
            raise UserNotFound()
        if user.status != UserStatus.ACTIVE:
            raise UserInactive()
        perms = self.authz.permissions_for_user(user)
        return user_to_dto(user, role=_resolve_role(user), permissions=list(perms))


@dataclass(frozen=True)
class ListUsersQuery:
    pass


@dataclass
class ListUsersHandler:
    user_repo: UserRepository
    authz: AuthorizationService

    async def execute(self, query: ListUsersQuery) -> list[UserDTO]:
        users = await self.user_repo.find_all()
        results: list[UserDTO] = []
        for user in users:
            perms = self.authz.permissions_for_user(user)
            results.append(user_to_dto(user, role=_resolve_role(user), permissions=list(perms)))
        return results


@dataclass(frozen=True)
class GetMyPermissionsQuery:
    user_id: str
    user: User | None = None


@dataclass
class GetMyPermissionsHandler:
    user_repo: UserRepository
    authz: AuthorizationService

    async def execute(self, query: GetMyPermissionsQuery) -> dict:
        user = query.user or await self.user_repo.find_by_id(query.user_id)
        if user is None:
            raise UserNotFound()
        perms = self.authz.permissions_for_user(user)
        return {
            "user_id": user.id,
            "permissions": list(perms),
        }
