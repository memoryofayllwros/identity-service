from __future__ import annotations

from dataclasses import dataclass

from src.application.ports.shared_kernel import SharedKernelPort
from src.domain.entities.tenant import Tenant
from src.domain.repositories import TenantRepository


@dataclass
class EnsureDefaultTenantHandler:
    tenant_repo: TenantRepository
    shared_kernel: SharedKernelPort
    tenant_instance_id: str

    async def execute(self) -> Tenant:
        existing = await self.tenant_repo.find_by_id(self.tenant_instance_id)
        if existing is not None:
            return existing

        slug = self.shared_kernel.default_tenant_slug
        name = self.shared_kernel.default_tenant_name
        plan = "enterprise"
        features = list(self.shared_kernel.plan_features(plan))

        tenant = Tenant.create(
            tenant_id=self.tenant_instance_id,
            name=name,
            slug=slug,
            features=features,
        )
        await self.tenant_repo.save(tenant)
        return tenant
