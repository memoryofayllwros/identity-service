from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from src.models._utils import HongKongDatetime, as_hk, new_id
from src.models.enums import UserRole


class MembershipDoc(Document):
    membership_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    tenant_id: Indexed(str)
    user_id: Indexed(str)
    # Legacy enum claim (kept for ver:1 / early clients)
    role: UserRole
    # Phase 3: RoleDoc.role_id list
    role_ids: list[str] = Field(default_factory=list)
    # Per-membership permission snapshot version (also mirrored on JWT)
    perm_ver: int = 1
    is_active: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "memberships"
        indexes = [
            [("tenant_id", 1), ("user_id", 1)],
            ("role",),
            ("is_active",),
        ]
