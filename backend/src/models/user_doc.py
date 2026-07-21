from typing import Optional

from beanie import Document, Indexed
from pydantic import Field

from src.models._utils import HongKongDatetime, as_hk, new_id
from src.models.embeds import MobileInfo
from src.models.enums import UserRole


class UserDoc(Document):
    user_id: Indexed(str, unique=True) = Field(default_factory=new_id)
    username: Indexed(str, unique=True)
    email: Indexed(str, unique=True)
    full_name: str
    phone: Optional[MobileInfo] = None
    password_hash: str
    role: UserRole
    is_outsourced: bool = False
    is_active: bool = True
    created_at: HongKongDatetime = Field(default_factory=as_hk)

    class Settings:
        name = "users"
        indexes = [("role",)]
