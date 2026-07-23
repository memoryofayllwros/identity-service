from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from src.application.dto import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    PhoneDTO,
    ProfileUpdate,
    RegisterRequest,
    UserResponse,
    mobile_digits_from_pair,
)

# HTTP-layer alias — routers and OpenAPI schema continue to see PhoneResponse
PhoneResponse = PhoneDTO


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


__all__ = [
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "LoginRequest",
    "LoginResponse",
    "OAuth2TokenResponse",
    "PhoneDTO",
    "PhoneResponse",
    "ProfileUpdate",
    "RegisterRequest",
    "UserResponse",
    "mobile_digits_from_pair",
]
