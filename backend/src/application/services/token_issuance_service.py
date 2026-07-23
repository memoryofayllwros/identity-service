from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import LoginResult, user_to_response
from src.application.ports.token_service import TokenService
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.membership import Membership
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User


@dataclass
class TokenIssuanceService:
    authz: AuthorizationService
    token_service: TokenService
    jwt_expire_minutes: int

    async def issue_login(
        self,
        user: User,
        membership: Membership,
        tenant: Tenant,
    ) -> LoginResult:
        perms = await self.authz.permissions_for_membership(membership)
        perm_ver = await self.authz.membership_perm_ver(membership, tenant)
        token = self.token_service.create_access_token(
            user.id,
            user.email.value,
            membership.role.value,
            tenant_id=membership.tenant_id,
            role_ids=list(membership.role_ids),
            perm_ver=perm_ver,
            scopes=list(perms)[:32],
        )
        refresh = self.token_service.create_refresh_token(
            user.id, tenant_id=membership.tenant_id
        )
        return LoginResult(
            access_token=token,
            expires_in_seconds=self.jwt_expire_minutes * 60,
            user=user_to_response(
                user,
                tenant_id=membership.tenant_id,
                tenant_name=tenant.name,
                role=membership.role,
                permissions=list(perms),
                perm_ver=perm_ver,
            ),
            refresh_token=refresh,
        )
