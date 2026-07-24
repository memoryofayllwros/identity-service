from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.infrastructure.persistence.mongo.embeds import MobileInfo
from src.domain.enums import UserRole, UserStatus


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[MobileInfo] = None
    position: str = ""
    role_code: str = "operations"
    is_outsourced: bool = False


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[MobileInfo] = None
    position: Optional[str] = None
    role_code: Optional[str] = None
    is_outsourced: Optional[bool] = None
    status: Optional[UserStatus] = None


class UserListResponse(BaseModel):
    user_id: str
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[MobileInfo] = None
    position: str = ""
    role: UserRole
    is_outsourced: bool
    status: UserStatus
    must_change_password: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDirectoryEntry(BaseModel):
    user_id: str
    full_name: str
    username: str

    model_config = ConfigDict(from_attributes=True)
