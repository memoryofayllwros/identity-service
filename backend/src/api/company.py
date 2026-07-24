"""Company profile API (single deployment tenant)."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler
from src.domain.exceptions import TenantNotFound
from src.infrastructure.dependencies import get_ensure_default_tenant_handler, get_tenant_repository
from src.infrastructure.security.dependencies import get_current_principal, require_permission
from src.infrastructure.security.principal import Principal
from src.shared.permissions import IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN

router = APIRouter(prefix="/company", tags=["company"])
CompanyAdminDep = Annotated[
    Principal,
    Depends(require_permission(IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN)),
]


class CompanyResponse(BaseModel):
    tenant_id: str
    name: str
    slug: str
    status: str
    features: list[str] = Field(default_factory=list)
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    features: Optional[list[str]] = None


def _company_response(tenant) -> CompanyResponse:
    return CompanyResponse(
        tenant_id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status.value,
        features=list(tenant.features),
        is_active=tenant.is_active,
    )


async def _current_company(handler: EnsureDefaultTenantHandler):
    return await handler.execute()


@router.get("", response_model=CompanyResponse)
async def get_company(
    _principal: Principal = Depends(get_current_principal),
    handler: EnsureDefaultTenantHandler = Depends(get_ensure_default_tenant_handler),
) -> CompanyResponse:
    tenant = await _current_company(handler)
    return _company_response(tenant)


@router.patch("", response_model=CompanyResponse)
async def update_company(
    payload: CompanyUpdateRequest,
    _principal: CompanyAdminDep,
    handler: EnsureDefaultTenantHandler = Depends(get_ensure_default_tenant_handler),
) -> CompanyResponse:
    tenant = await _current_company(handler)
    updates = payload.model_dump(exclude_unset=True)
    tenant.update_profile(
        name=updates.get("name"),
        features=updates.get("features"),
    )
    await get_tenant_repository().save(tenant)
    refreshed = await get_tenant_repository().find_by_id(tenant.id)
    if refreshed is None:
        raise TenantNotFound()
    return _company_response(refreshed)
