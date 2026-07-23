from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import InviteResult
from src.application.services.authorization_service import AuthorizationError, AuthorizationService
from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.invite import Invite
from src.domain.exceptions import Forbidden, InvalidRoleCode, TenantNotFound
from src.domain.id_generator import IDGenerator
from src.domain.repositories import AuthEventRepository, InviteRepository, TenantRepository
from src.domain.unit_of_work import UnitOfWork
from src.application.principal import Principal


@dataclass
class InviteUserCommand:
    tenant_id: str
    email: str
    role_code: str
    actor: Principal


class InviteUserHandler:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        invite_repo: InviteRepository,
        authz: AuthorizationService,
        auth_events: AuthEventRepository,
        uow: UnitOfWork,
        id_gen: IDGenerator,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._invite_repo = invite_repo
        self._authz = authz
        self._auth_events = auth_events
        self._uow = uow
        self._id_gen = id_gen

    async def execute(self, command: InviteUserCommand) -> InviteResult:
        from src.shared.permissions import IDENTITY_INVITE_MANAGE, IDENTITY_TENANT_ADMIN

        try:
            self._authz.check_permission(
                command.actor, IDENTITY_INVITE_MANAGE, IDENTITY_TENANT_ADMIN
            )
        except AuthorizationError as exc:
            raise Forbidden(str(exc)) from exc

        tenant = await self._tenant_repo.find_by_id(command.tenant_id)
        if tenant is None:
            raise TenantNotFound()

        if command.role_code not in ("admin", "operations"):
            raise InvalidRoleCode()

        await self._authz.ensure_tenant_roles(command.tenant_id)
        invite = Invite.create(
            invite_id=self._id_gen(),
            tenant_id=command.tenant_id,
            email=command.email,
            token=self._id_gen(),
            role_code=command.role_code,
            invited_by_user_id=command.actor.user_id,
        )

        async with self._uow:
            self._uow.register(invite)
            await self._uow.commit()

        await self._auth_events.save(
            AuthEvent.record(
                event_id=self._id_gen(),
                event_type="invite.created",
                tenant_id=command.tenant_id,
                actor_user_id=command.actor.user_id,
                detail={"email": str(invite.email), "role_code": invite.role_code},
            )
        )
        return InviteResult(invite=invite)
