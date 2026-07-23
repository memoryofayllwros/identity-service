from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import TenantResult
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.user import User
from src.domain.enums import UserRole
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
from src.application.ports.password_hasher import PasswordHasher
from src.domain.id_generator import IDGenerator
from src.domain.unit_of_work import UnitOfWork


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
        membership_service: object,
        uow: UnitOfWork,
        id_gen: IDGenerator,
        password_hasher: PasswordHasher,
    ) -> None:
        self._invite_repo = invite_repo
        self._tenant_repo = tenant_repo
        self._user_repo = user_repo
        self._membership_repo = membership_repo
        self._authz = authz
        self._auth_events = auth_events
        self._membership_service = membership_service
        self._uow = uow
        self._id_gen = id_gen
        self._password_hasher = password_hasher

    async def execute(self, command: AcceptInviteCommand) -> TenantResult:
        invite = await self._invite_repo.find_by_token(command.token)
        if invite is None or not invite.is_pending:
            raise InviteNotFound()

        tenant = await self._tenant_repo.find_by_id(invite.tenant_id)
        if tenant is None or tenant.is_suspended:
            raise TenantSuspended()

        if await self._user_repo.find_by_email(str(invite.email)):
            raise DuplicateEmail("Email already registered.")
        if await self._user_repo.find_by_username(command.username):
            raise DuplicateUsername()

        role = UserRole.ADMIN if invite.role_code == "admin" else UserRole.OPERATIONS
        user = User.register(
            user_id=self._id_gen(),
            username=command.username,
            email=invite.email,
            full_name=command.full_name,
            password_hash=self._password_hasher.hash(command.password),
            tenant_id=tenant.id,
        )

        try:
            invite.accept(user_id=user.id)
        except InviteExpired:
            async with self._uow:
                self._uow.register(invite)
                await self._uow.commit()
            raise
        except InviteNotPending:
            raise InviteNotFound()

        async with self._uow:
            self._uow.register(user)
            self._uow.register(invite)
            await self._membership_service.ensure_membership(
                tenant_id=tenant.id,
                user_id=user.id,
                role=role,
                uow=self._uow,
            )
            await self._uow.commit()

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
        refreshed = await self._tenant_repo.find_by_id(tenant.id)
        return TenantResult(tenant=refreshed or tenant)
