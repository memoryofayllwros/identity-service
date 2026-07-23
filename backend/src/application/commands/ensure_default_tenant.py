from __future__ import annotations

from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.tenant import Tenant
from src.domain.enums import TenantStatus
from src.domain.events import TenantCreated
from src.domain.repositories import TenantRepository
from src.domain.events.publisher import EventPublisher
from src.shared.constants import DEFAULT_TENANT_NAME, DEFAULT_TENANT_SLUG
from src.shared.permissions import PLAN_FEATURES


class EnsureDefaultTenantHandler:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        authz: AuthorizationService,
        publisher: EventPublisher,
        tenant_instance_id: str,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._authz = authz
        self._publisher = publisher
        self._tenant_instance_id = tenant_instance_id

    async def execute(self) -> Tenant:
        tenant_id = self._tenant_instance_id
        tenant = await self._tenant_repo.find_by_id(tenant_id)
        if tenant is not None:
            if tenant.id != tenant_id:
                raise RuntimeError("Configured TENANT_INSTANCE_ID does not match tenant record.")
            await self._authz.ensure_tenant_roles(tenant.id)
            return tenant

        await self._authz.ensure_platform_role_templates()
        features = list(PLAN_FEATURES.get("enterprise", []))
        slug = tenant_id or DEFAULT_TENANT_SLUG
        tenant = Tenant(
            id=tenant_id,
            name=DEFAULT_TENANT_NAME,
            slug=slug,
            plan="enterprise",
            status=TenantStatus.ACTIVE,
            features=features,
            is_active=True,
            perm_ver=1,
        )
        await self._tenant_repo.save(tenant)
        await self._authz.ensure_tenant_roles(tenant.id)
        await self._publisher.publish(
            TenantCreated(tenant_id=tenant.id, name=tenant.name, slug=tenant.slug)
        )
        return tenant
