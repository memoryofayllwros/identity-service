from __future__ import annotations

from dataclasses import dataclass

from src.application.dto import TenantResult
from src.application.services.authorization_service import AuthorizationError, AuthorizationService
from src.domain.entities.auth_event import AuthEvent
from src.domain.events import TenantSuspended
from src.domain.exceptions import TenantAlreadySuspended
from src.domain.repositories import AuthEventRepository, TenantRepository
from src.infrastructure.messaging.event_publisher import EventPublisher
from src.infrastructure.persistence.mongo._utils import new_id
from src.security.principal import Principal
from src.shared.permissions import IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN


@dataclass
class SuspendTenantCommand:
    tenant_id: str
    actor: Principal
    reason: str | None = None


class SuspendTenantHandler:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        authz: AuthorizationService,
        auth_events: AuthEventRepository,
        publisher: EventPublisher,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._authz = authz
        self._auth_events = auth_events
        self._publisher = publisher

    async def execute(self, command: SuspendTenantCommand) -> TenantResult:
        from fastapi import HTTPException, status
        from src.domain.enums import UserRole

        try:
            self._authz.check_permission(
                command.actor, IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN
            )
        except AuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        if command.actor.tenant_id != command.tenant_id and command.actor.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

        tenant = await self._tenant_repo.find_by_id(command.tenant_id)
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

        try:
            tenant.suspend()
        except TenantAlreadySuspended:
            pass

        await self._tenant_repo.save(tenant)
        await self._authz.bump_tenant_perm_ver(tenant.id)
        await self._auth_events.save(
            AuthEvent.record(
                event_id=new_id(),
                event_type="tenant.suspended",
                tenant_id=tenant.id,
                actor_user_id=command.actor.user_id,
                detail={"reason": command.reason},
            )
        )
        await self._publisher.publish(
            TenantSuspended(tenant_id=tenant.id, reason=command.reason)
        )
        return TenantResult(tenant=tenant)


@dataclass
class ActivateTenantCommand:
    tenant_id: str
    actor: Principal


class ActivateTenantHandler:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        authz: AuthorizationService,
        auth_events: AuthEventRepository,
        publisher: EventPublisher,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._authz = authz
        self._auth_events = auth_events
        self._publisher = publisher

    async def execute(self, command: ActivateTenantCommand) -> TenantResult:
        from fastapi import HTTPException, status

        from src.shared.permissions import PLAN_FEATURES

        try:
            self._authz.check_permission(
                command.actor, IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN
            )
        except AuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        tenant = await self._tenant_repo.find_by_id(command.tenant_id)
        if tenant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")

        features = list(tenant.features) or list(PLAN_FEATURES.get(tenant.plan, []))
        tenant.activate(features=features)
        await self._tenant_repo.save(tenant)
        await self._authz.bump_tenant_perm_ver(tenant.id)
        await self._auth_events.save(
            AuthEvent.record(
                event_id=new_id(),
                event_type="tenant.activated",
                tenant_id=tenant.id,
                actor_user_id=command.actor.user_id,
            )
        )
        return TenantResult(tenant=tenant)
