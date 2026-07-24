from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import LoginResult, user_to_dto
from src.application.ports.token_service import TokenService
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.shared.constants import DEFAULT_TENANT_ID
from src.shared.permissions import IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN


@dataclass
class TokenIssuanceService:
    authz: AuthorizationService
    token_service: TokenService
    jwt_expire_minutes: int

    def _resolve_role(self, user: User) -> UserRole:
        admin_markers = {IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN}
        if admin_markers.intersection(user.permissions):
            return UserRole.ADMIN
        return UserRole.OPERATIONS

    async def issue_login(self, user: User) -> LoginResult:
        perms = self.authz.permissions_for_user(user)
        role = self._resolve_role(user)
        token = self.token_service.create_access_token(
            user.id,
            user.email.value,
            role.value,
            tenant_id=DEFAULT_TENANT_ID,
            role_ids=[],
            perm_ver=1,
            scopes=list(perms)[:32],
        )
        refresh = self.token_service.create_refresh_token(user.id, tenant_id=DEFAULT_TENANT_ID)
        return LoginResult(
            access_token=token,
            expires_in_seconds=self.jwt_expire_minutes * 60,
            user=user_to_dto(user, role=role, permissions=list(perms)),
            refresh_token=refresh,
        )
