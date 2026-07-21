from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import TenantResult
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.events import InviteAccepted, UserRegistered
from src.domain.exceptions import InviteExpired, InviteNotPending
from src.domain.repositories import (
    AuthEventRepository,
    InviteRepository,
    MembershipRepository,
    TenantRepository,
    UserRepository,
)
from src.infrastructure.messaging.event_publisher import EventPublisher
from src.infrastructure.persistence.mongo._utils import new_id
from src.security.security import hash_password


@dataclass
class AcceptInviteCommand:
    token: str
    username: str
    full_name: str
    password: str


class AcceptInviteHandler:
    def __init__(
        self,
        invite_repo: InviteRepository,
        tenant_repo: TenantRepository,
        user_repo: UserRepository,
        membership_repo: MembershipRepository,
        authz: AuthorizationService,
        auth_events: AuthEventRepository,
        publisher: EventPublisher,
        membership_service: object,
    ) -> None:
        self._invite_repo = invite_repo
        self._tenant_repo = tenant_repo
        self._user_repo = user_repo
        self._membership_repo = membership_repo
        self._authz = authz
        self._auth_events = auth_events
        self._publisher = publisher
        self._membership_service = membership_service

    async def execute(self, command: AcceptInviteCommand) -> TenantResult:
        from fastapi import HTTPException, status

        invite = await self._invite_repo.find_by_token(command.token)
        if invite is None or not invite.is_pending:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")
        try:
            invite.accept()
        except InviteExpired:
            await self._invite_repo.save(invite)
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invite expired.") from None
        except InviteNotPending:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.") from None

        tenant = await self._tenant_repo.find_by_id(invite.tenant_id)
        if tenant is None or tenant.is_suspended:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is suspended.")

        if await self._user_repo.find_by_email(invite.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
        if await self._user_repo.find_by_username(command.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

        role = UserRole.ADMIN if invite.role_code == "admin" else UserRole.OPERATIONS
        user = User(
            id=new_id(),
            username=command.username,
            email=invite.email,
            full_name=command.full_name,
            password_hash=hash_password(command.password),
        )
        await self._user_repo.save(user)
        await self._membership_service.ensure_membership(
            tenant_id=tenant.id,
            user_id=user.id,
            role=role,
        )
        await self._invite_repo.save(invite)
        await self._authz.bump_tenant_perm_ver(tenant.id)
        await self._auth_events.save(
            AuthEvent.record(
                event_id=new_id(),
                event_type="invite.accepted",
                tenant_id=tenant.id,
                user_id=user.id,
                detail={"invite_id": invite.id},
            )
        )
        await self._publisher.publish(
            InviteAccepted(invite_id=invite.id, tenant_id=tenant.id, user_id=user.id)
        )
        await self._publisher.publish(
            UserRegistered(user_id=user.id, email=user.email, tenant_id=tenant.id)
        )
        refreshed = await self._tenant_repo.find_by_id(tenant.id)
        return TenantResult(tenant=refreshed or tenant)
