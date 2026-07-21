from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.models.embeds import MobileInfo
from src.models.enums import UserRole


def mobile_digits_from_pair(country_code: str, phone_number: str) -> str:
    cc = country_code.strip().lstrip("+")
    return f"{cc}{phone_number.strip()}"


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    phone: Optional[MobileInfo] = None
    role: UserRole = UserRole.OPERATIONS
    is_outsourced: bool = False


class LoginRequest(BaseModel):
    """Login with username, email, or phone digits (country_code + phone_number)."""

    mobile: str = Field(..., min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("mobile", mode="before")
    @classmethod
    def normalize_login_identifier(cls, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            pair = MobileInfo.model_validate(value)
            return mobile_digits_from_pair(pair.country_code, pair.phone_number)
        raise TypeError("mobile must be a string or {country_code, phone_number}")


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    phone: Optional[MobileInfo] = None
    role: UserRole
    is_outsourced: bool
    is_active: bool
    created_at: datetime
    tenant_id: str
    tenant_name: Optional[str] = None
    permissions: Optional[list[str]] = None
    perm_ver: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse
    refresh_token: Optional[str] = None


class OAuth2TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[MobileInfo] = None


class ForgotPasswordRequest(BaseModel):
    mobile: str = Field(..., min_length=1, max_length=128)

    @field_validator("mobile", mode="before")
    @classmethod
    def normalize_login_identifier(cls, value: object) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            pair = MobileInfo.model_validate(value)
            return mobile_digits_from_pair(pair.country_code, pair.phone_number)
        raise TypeError("mobile must be a string or {country_code, phone_number}")


class ForgotPasswordResponse(BaseModel):
    message: str
