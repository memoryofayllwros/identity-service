"""Permission catalog entry (optional registry; codes also live on RoleDoc)."""

from beanie import Document, Indexed
from pydantic import Field

from src.models._utils import HongKongDatetime, as_hk, new_id


class PermissionDoc(Document):
    permission_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    code: Indexed(str, unique=True)
    description: str = ""
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "permissions"
