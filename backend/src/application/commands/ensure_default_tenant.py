from __future__ import annotations

from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.tenant import Tenant
from src.domain.repositories import TenantRepository
from src.domain.unit_of_work import UnitOfWork


class EnsureDefaultTenantHandler:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        authz: AuthorizationService,
        uow: UnitOfWork,
        tenant_instance_id: str,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._authz = authz
        self._uow = uow
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
        kernel = self._authz.shared_kernel
        features = list(kernel.plan_features("enterprise"))
        slug = tenant_id or kernel.default_tenant_slug
        tenant = Tenant.create(
            tenant_id=tenant_id,
            name=kernel.default_tenant_name,
            slug=slug,
            plan="enterprise",
            features=features,
            perm_ver=1,
        )

        async with self._uow:
            self._uow.register(tenant)
            await self._uow.commit()

        await self._authz.ensure_tenant_roles(tenant.id)
        return tenant
