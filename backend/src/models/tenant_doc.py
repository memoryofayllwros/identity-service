from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from src.models._utils import HongKongDatetime, as_hk, new_id


class TenantDoc(Document):
    tenant_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    name: str
    slug: Indexed(str, unique=True)
    plan: str = "enterprise"
    # active | suspended | pending
    status: str = "active"
    features: list[str] = Field(default_factory=list)
    is_active: bool = True
    # Bumped when any membership/role permission changes in this tenant
    perm_ver: int = 1
    created_at: HongKongDatetime = Field(default_factory=as_hk)
    suspended_at: Optional[HongKongDatetime] = None

    class Settings:
        name = "tenants"
        indexes = [("is_active",), ("status",), ("plan",)]
