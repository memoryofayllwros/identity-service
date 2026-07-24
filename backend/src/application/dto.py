from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domain.entities.invite import Invite
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import UserRole


class PhoneDTO(BaseModel):
    country_code: str = Field(min_length=1, max_length=8)
    phone_number: str = Field(min_length=1, max_length=32)


def mobile_digits_from_pair(country_code: str, phone_number: str) -> str:
    cc = country_code.strip().lstrip("+")
    return f"{cc}{phone_number.strip()}"


class RegisterDTO(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[PhoneDTO] = None
    role: UserRole = UserRole.OPERATIONS
    is_outsourced: bool = False


class LoginDTO(BaseModel):
    """Login with username, email, or phone digits (country_code + phone_number)."""

    mobile: str = Field(..., min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("mobile", mode="before")
    @classmethod
    def normalize_login_identifier(cls, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            pair = PhoneDTO.model_validate(value)
            return mobile_digits_from_pair(pair.country_code, pair.phone_number)
        raise TypeError("mobile must be a string or {country_code, phone_number}")


class UserDTO(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[PhoneDTO] = None
    role: UserRole
    is_outsourced: bool
    is_active: bool
    created_at: datetime
    tenant_id: str
    tenant_name: Optional[str] = None
    permissions: Optional[list[str]] = None
    perm_ver: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateDTO(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[PhoneDTO] = None


class ForgotPasswordDTO(BaseModel):
    mobile: str = Field(..., min_length=1, max_length=128)


class ForgotPasswordResultDTO(BaseModel):
    message: str


def user_to_dto(
    user: User,
    *,
    tenant_id: str,
    tenant_name: str | None = None,
    role: UserRole,
    permissions: list[str] | None = None,
    perm_ver: int | None = None,
) -> UserDTO:
    phone = None
    if user.phone:
        phone = PhoneDTO(
            country_code=user.phone.country_code,
            phone_number=user.phone.phone_number,
        )
    return UserDTO(
        id=user.id,
        email=user.email.value,
        username=user.username,
        full_name=user.full_name,
        phone=phone,
        role=role,
        is_outsourced=user.is_outsourced,
        is_active=user.is_active,
        created_at=user.created_at or datetime.now(),
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        permissions=permissions,
        perm_ver=perm_ver,
    )


@dataclass
class InviteResult:
    invite: Invite


@dataclass
class TenantResult:
    tenant: Tenant


@dataclass
class LoginResult:
    access_token: str
    expires_in_seconds: int
    user: UserDTO
    refresh_token: str | None = None
