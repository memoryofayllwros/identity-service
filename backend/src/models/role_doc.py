"""RBAC Role document (platform template or per-tenant custom)."""

from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from src.models._utils import HongKongDatetime, as_hk, new_id


class RoleDoc(Document):
    role_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    # None = platform template; set for per-tenant custom roles
    tenant_id: Optional[Indexed(str)] = None
    code: Indexed(str)
    name: str
    permissions: list[str] = Field(default_factory=list)
    is_system: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "roles"
        indexes = [
            [("tenant_id", 1), ("code", 1)],
            ("is_system",),
        ]
