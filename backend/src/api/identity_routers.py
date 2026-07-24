"""Identity Platform HTTP API (auth, users, JWKS)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from datetime import datetime

from src.application.commands.create_user import CreateUserCommand
from src.application.services.authorization_service import AuthorizationService
from src.domain.entities.user import User
from src.domain.enums import UserRole, UserStatus
from src.domain.exceptions import InvalidRoleCode
from src.infrastructure.dependencies import (
    get_authorization_service,
    get_create_user_handler,
    get_role_repository,
    get_user_repository,
)
from src.schemas.common import PaginatedResponse
from src.schemas.reference import UserCreate, UserDirectoryEntry, UserListResponse, UserUpdate
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone
from src.infrastructure.security.dependencies import require_permission
from src.infrastructure.security.jwt_keys import build_jwks
from src.infrastructure.security.principal import Principal
from src.shared.permissions import IDENTITY_USER_ADMIN, IDENTITY_USER_READ

from src.api.auth import router as auth_router
from src.api.company import router as company_router
from src.api.health import router as health_router
from src.api.identity_ops import router as identity_ops_router

users_router = APIRouter(prefix="/users", tags=["users"])
AdminDep = Annotated[Principal, Depends(require_permission(IDENTITY_USER_ADMIN))]
ReadDep = Annotated[Principal, Depends(require_permission(IDENTITY_USER_READ, IDENTITY_USER_ADMIN))]


def _resolve_role(user: User, authz: AuthorizationService) -> UserRole:
    role_code = authz.infer_role_from_permissions(user.permissions)
    return UserRole.ADMIN if role_code == authz.shared_kernel.role_code_admin else UserRole.OPERATIONS


def _user_list_response(user: User, role: UserRole) -> UserListResponse:
    phone = None
    if user.phone:
        from src.infrastructure.persistence.mongo.embeds import MobileInfo

        phone = MobileInfo(
            country_code=user.phone.country_code,
            phone_number=user.phone.phone_number,
        )
    return UserListResponse(
        user_id=user.id,
        email=user.email.value,
        username=user.username,
        full_name=user.full_name,
        phone=phone,
        position=user.position,
        role=role,
        is_outsourced=user.is_outsourced,
        status=user.status,
        must_change_password=user.must_change_password,
        created_at=user.created_at or datetime.now(),
    )


@users_router.get("", response_model=PaginatedResponse[UserListResponse])
async def list_users(
    _user: AdminDep,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedResponse[UserListResponse]:
    limit = min(max(limit, 1), 200)
    skip = max(skip, 0)
    authz = get_authorization_service()
    users = await get_user_repository().find_all()
    total = len(users)
    page = users[skip : skip + limit]
    items = [_user_list_response(user, _resolve_role(user, authz)) for user in page]
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@users_router.post("", response_model=UserListResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, principal: AdminDep) -> UserListResponse:
    phone = None
    if payload.phone:
        phone = Phone(
            country_code=payload.phone.country_code,
            phone_number=payload.phone.phone_number,
        )
    result = await get_create_user_handler().execute(
        CreateUserCommand(
            username=payload.username,
            email=str(payload.email),
            full_name=payload.full_name,
            password=payload.password,
            role_code=payload.role_code,
            position=payload.position,
            is_outsourced=payload.is_outsourced,
            phone=phone,
            created_by_user_id=principal.user_id,
        )
    )
    user = await get_user_repository().find_by_id(result.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User not found.")
    return _user_list_response(user, result.role)


@users_router.get("/by-ids", response_model=list[UserDirectoryEntry])
async def get_users_by_ids(
    _user: ReadDep,
    ids: str = Query(..., min_length=1, description="Comma-separated user IDs"),
) -> list[UserDirectoryEntry]:
    requested = [part.strip() for part in ids.split(",") if part.strip()][:50]
    if not requested:
        return []
    users = await get_user_repository().find_all()
    by_id = {u.id: u for u in users if u.id in requested}
    return [
        UserDirectoryEntry(user_id=u.id, full_name=u.full_name, username=u.username)
        for user_id in requested
        if (u := by_id.get(user_id))
    ]


@users_router.get("/{user_id}", response_model=UserListResponse)
async def get_user(user_id: str, _user: ReadDep) -> UserListResponse:
    user = await get_user_repository().find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    authz = get_authorization_service()
    return _user_list_response(user, _resolve_role(user, authz))


@users_router.patch("/{user_id}", response_model=UserListResponse)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    _user: AdminDep,
) -> UserListResponse:
    user = await get_user_repository().find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    authz = get_authorization_service()
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        existing = await get_user_repository().find_by_email(str(updates["email"]))
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")
    if "full_name" in updates:
        user.full_name = updates["full_name"]
    if "email" in updates:
        user.email = Email(str(updates["email"]))
    if "phone" in updates and updates["phone"] is not None:
        user.phone = Phone(
            country_code=updates["phone"].country_code,
            phone_number=updates["phone"].phone_number,
        )
    if "position" in updates:
        user.position = updates["position"]
    if "is_outsourced" in updates:
        user.is_outsourced = updates["is_outsourced"]
    if "status" in updates and updates["status"] is not None:
        status_value = updates["status"]
        if status_value == UserStatus.ACTIVE:
            user.activate()
        elif status_value == UserStatus.SUSPENDED:
            user.suspend()
        elif status_value == UserStatus.DEACTIVATED:
            user.deactivate()
    if "role_code" in updates and updates["role_code"] is not None:
        role = await get_role_repository().find_by_code(updates["role_code"])
        if role is None:
            raise InvalidRoleCode(f"Unknown role_code: {updates['role_code']}")
        user.assign_permissions(list(role.permissions))
    await get_user_repository().save(user)
    refreshed = await get_user_repository().find_by_id(user_id)
    return _user_list_response(refreshed or user, _resolve_role(refreshed or user, authz))


jwks_router = APIRouter(tags=["jwks"])


@jwks_router.get("/.well-known/jwks.json")
async def jwks() -> dict:
    return build_jwks()


IDENTITY_ROUTERS = [
    health_router,
    auth_router,
    company_router,
    users_router,
    identity_ops_router,
    jwks_router,
]
