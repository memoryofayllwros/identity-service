from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import TenantResult
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.events import InviteAccepted, UserRegistered
from src.domain.exceptions import (
    DuplicateEmail,
    DuplicateUsername,
    InviteExpired,
    InviteNotFound,
    InviteNotPending,
    TenantSuspended,
)
from src.domain.repositories import (
    AuthEventRepository,
    InviteRepository,
    MembershipRepository,
    TenantRepository,
    UserRepository,
)
from src.domain.events.publisher import EventPublisher
from src.application.ports.password_hasher import PasswordHasher
from src.domain.id_generator import IDGenerator


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
        id_gen: IDGenerator,
        password_hasher: PasswordHasher,
    ) -> None:
        self._invite_repo = invite_repo
        self._tenant_repo = tenant_repo
        self._user_repo = user_repo
        self._membership_repo = membership_repo
        self._authz = authz
        self._auth_events = auth_events
        self._publisher = publisher
        self._membership_service = membership_service
        self._id_gen = id_gen
        self._password_hasher = password_hasher

    async def execute(self, command: AcceptInviteCommand) -> TenantResult:
        invite = await self._invite_repo.find_by_token(command.token)
        if invite is None or not invite.is_pending:
            raise InviteNotFound()
        try:
            invite.accept()
        except InviteExpired:
            await self._invite_repo.save(invite)
            raise
        except InviteNotPending:
            raise InviteNotFound()

        tenant = await self._tenant_repo.find_by_id(invite.tenant_id)
        if tenant is None or tenant.is_suspended:
            raise TenantSuspended()

        if await self._user_repo.find_by_email(str(invite.email)):
            raise DuplicateEmail("Email already registered.")
        if await self._user_repo.find_by_username(command.username):
            raise DuplicateUsername()

        role = UserRole.ADMIN if invite.role_code == "admin" else UserRole.OPERATIONS
        user = User(
            id=self._id_gen(),
            username=command.username,
            email=invite.email,
            full_name=command.full_name,
            password_hash=self._password_hasher.hash(command.password),
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
                event_id=self._id_gen(),
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
            UserRegistered(user_id=user.id, email=user.email.value, tenant_id=tenant.id)
        )
        refreshed = await self._tenant_repo.find_by_id(tenant.id)
        return TenantResult(tenant=refreshed or tenant)
