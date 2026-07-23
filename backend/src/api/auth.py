from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from src.application.queries.user_queries import GetMyPermissionsQuery, GetUserQuery, ListUsersQuery
from src.infrastructure.dependencies import (
    get_auth_application_service,
    get_get_user_handler,
    get_list_users_handler,
    get_my_permissions_handler,
    get_user_repository,
)
from src.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    OAuth2TokenResponse,
    ProfileUpdate,
    RegisterRequest,
    UserResponse,
)
from src.infrastructure.security.dependencies import get_current_principal, require_roles
from src.domain.enums import UserRole
from src.infrastructure.security.principal import Principal
from src.infrastructure.security.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])
AdminDep = Annotated[Principal, Depends(require_roles(UserRole.ADMIN))]


class MobileOAuth2PasswordRequestForm(OAuth2PasswordRequestForm):
    def __init__(
        self,
        grant_type: Optional[str] = Form(default=None, pattern="password"),
        username: str = Form(...),
        password: str = Form(...),
        scope: str = Form(default=""),
        client_id: Optional[str] = Form(default=None),
        client_secret: Optional[str] = Form(default=None),
    ):
        super().__init__(
            grant_type=grant_type,
            username=username,
            password=password,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
        )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


def _login_response(result) -> LoginResponse:
    return LoginResponse(
        access_token=result.access_token,
        expires_in_seconds=result.expires_in_seconds,
        user=result.user,
        refresh_token=result.refresh_token,
    )


@router.post("/token", response_model=OAuth2TokenResponse)
async def login_for_access_token(
    request: Request,
    form_data: MobileOAuth2PasswordRequestForm = Depends(),
) -> OAuth2TokenResponse:
    enforce_rate_limit(request, suffix="auth.login", max_hits=30, window_seconds=60)
    result = await get_auth_application_service().login(
        LoginRequest(mobile=form_data.username, password=form_data.password)
    )
    return OAuth2TokenResponse(
        access_token=result.access_token,
        expires_in=result.expires_in_seconds,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: Request, payload: RegisterRequest) -> UserResponse:
    enforce_rate_limit(request, suffix="auth.register", max_hits=10, window_seconds=60)
    return await get_auth_application_service().register(payload)


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest) -> LoginResponse:
    enforce_rate_limit(request, suffix="auth.login", max_hits=30, window_seconds=60)
    return _login_response(await get_auth_application_service().login(payload))


@router.post("/refresh", response_model=LoginResponse)
async def refresh(payload: RefreshRequest) -> LoginResponse:
    return _login_response(await get_auth_application_service().refresh(payload.refresh_token))


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
    return await get_auth_application_service().request_password_reset(payload)


@router.get("/me", response_model=UserResponse)
async def me(principal: Principal = Depends(get_current_principal)) -> UserResponse:
    user = await get_user_repository().find_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return await get_get_user_handler().execute(GetUserQuery(user_id=principal.user_id, user=user))


@router.get("/me/permissions")
async def me_permissions(principal: Principal = Depends(get_current_principal)) -> dict:
    user = await get_user_repository().find_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return await get_my_permissions_handler().execute(
        GetMyPermissionsQuery(user_id=principal.user_id, user=user)
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: ProfileUpdate,
    principal: Principal = Depends(get_current_principal),
) -> UserResponse:
    user = await get_user_repository().find_by_id(principal.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return await get_auth_application_service().update_profile(user, payload)


@router.get("/users", response_model=list[UserResponse])
async def list_users(_current_user: AdminDep) -> list[UserResponse]:
    return await get_list_users_handler().execute(ListUsersQuery())
