from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.domain.entities.user import User
from src.domain.enums import UserRole, UserStatus


class PhoneDTO(BaseModel):
    country_code: str = Field(min_length=1, max_length=8)
    phone_number: str = Field(min_length=1, max_length=32)


def mobile_from_pair(country_code: str, phone_number: str) -> str:
    cc = country_code.strip().lstrip("+")
    return f"+{cc}{phone_number.strip()}"


def normalize_mobile_identifier(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("+"):
        return stripped
    if stripped.isdigit():
        return f"+{stripped}"
    return stripped


class RegisterDTO(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[PhoneDTO] = None
    position: str = ""
    is_outsourced: bool = False


class LoginDTO(BaseModel):
    """Login with username, email, or mobile (+country_code + phone_number)."""

    mobile: str = Field(..., min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("mobile", mode="before")
    @classmethod
    def normalize_login_identifier(cls, value: object) -> str:
        if isinstance(value, str):
            return normalize_mobile_identifier(value)
        if isinstance(value, dict):
            pair = PhoneDTO.model_validate(value)
            return mobile_from_pair(pair.country_code, pair.phone_number)
        raise TypeError("mobile must be a string or {country_code, phone_number}")


class ChangePasswordDTO(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserDTO(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[PhoneDTO] = None
    position: str = ""
    role: UserRole
    is_outsourced: bool
    status: UserStatus
    must_change_password: bool
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateDTO(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[PhoneDTO] = None
    position: Optional[str] = None


class ForgotPasswordDTO(BaseModel):
    mobile: str = Field(..., min_length=1, max_length=128)


class ForgotPasswordResultDTO(BaseModel):
    message: str


def user_to_dto(
    user: User,
    *,
    role: UserRole | None = None,
    permissions: list[str] | None = None,
) -> UserDTO:
    from src.shared.permissions import IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN

    phone = None
    if user.phone:
        phone = PhoneDTO(
            country_code=user.phone.country_code,
            phone_number=user.phone.phone_number,
        )
    perms = permissions if permissions is not None else list(user.permissions)
    resolved_role = role
    if resolved_role is None:
        admin_markers = {IDENTITY_TENANT_ADMIN, IDENTITY_USER_ADMIN}
        resolved_role = (
            UserRole.ADMIN if admin_markers.intersection(perms) else UserRole.OPERATIONS
        )
    return UserDTO(
        id=user.id,
        email=user.email.value,
        username=user.username,
        full_name=user.full_name,
        phone=phone,
        position=user.position,
        role=resolved_role,
        is_outsourced=user.is_outsourced,
        status=user.status,
        must_change_password=user.must_change_password,
        permissions=list(perms),
        created_at=user.created_at or datetime.now(),
        last_login_at=user.last_login_at,
    )


@dataclass
class LoginResult:
    access_token: str
    expires_in_seconds: int
    user: UserDTO
    refresh_token: str | None = None
