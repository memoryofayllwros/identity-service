from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from src.application.dto import (
    ChangePasswordDTO,
    ForgotPasswordDTO,
    ForgotPasswordResultDTO,
    LoginDTO,
    PhoneDTO,
    ProfileUpdateDTO,
    RegisterDTO,
    UserDTO,
    mobile_from_pair,
    normalize_mobile_identifier,
)

# HTTP-layer aliases — routers and OpenAPI keep transport-oriented names.
PhoneResponse = PhoneDTO
UserResponse = UserDTO
RegisterRequest = RegisterDTO
LoginRequest = LoginDTO
ProfileUpdate = ProfileUpdateDTO
ForgotPasswordRequest = ForgotPasswordDTO
ForgotPasswordResponse = ForgotPasswordResultDTO
ChangePasswordRequest = ChangePasswordDTO


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserDTO
    refresh_token: Optional[str] = None


class OAuth2TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


__all__ = [
    "ChangePasswordDTO",
    "ChangePasswordRequest",
    "ForgotPasswordDTO",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ForgotPasswordResultDTO",
    "LoginDTO",
    "LoginRequest",
    "LoginResponse",
    "OAuth2TokenResponse",
    "PhoneDTO",
    "PhoneResponse",
    "ProfileUpdate",
    "ProfileUpdateDTO",
    "RegisterDTO",
    "RegisterRequest",
    "UserDTO",
    "UserResponse",
    "mobile_from_pair",
    "normalize_mobile_identifier",
]
