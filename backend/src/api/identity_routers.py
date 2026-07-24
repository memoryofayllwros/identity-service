"""Identity Platform HTTP API (auth, users, tenants, JWKS)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from datetime import datetime

from src.domain.entities.user import User
from src.domain.enums import UserRole
from src.domain.events import UserAddedToTenant
from src.infrastructure.dependencies import (
    build_event_publisher,
    ensure_membership,
    get_membership_repository,
    get_user_repository,
)
from src.infrastructure.persistence.mongo._utils import new_id
from src.schemas.common import PaginatedResponse
from src.schemas.reference import UserCreate, UserDirectoryEntry, UserListResponse, UserUpdate
from src.domain.value_objects.email import Email
from src.infrastructure.security.dependencies import require_permission
from src.infrastructure.security.jwt_keys import build_jwks
from src.infrastructure.security.principal import Principal
from src.infrastructure.security.security import hash_password
from src.shared.permissions import IDENTITY_USER_ADMIN, IDENTITY_USER_READ
from src.shared.tenant_context import current_tenant_id

from src.api.auth import router as auth_router
from src.api.health import router as health_router
from src.api.identity_ops import router as identity_ops_router
from src.api.tenants import router as tenants_router

users_router = APIRouter(prefix="/users", tags=["users"])
AdminDep = Annotated[Principal, Depends(require_permission(IDENTITY_USER_ADMIN))]
ReadDep = Annotated[Principal, Depends(require_permission(IDENTITY_USER_READ, IDENTITY_USER_ADMIN))]


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
        role=role,
        is_outsourced=user.is_outsourced,
        is_active=user.is_active,
        created_at=user.created_at or datetime.now(),
    )


async def _role_for_user(user_id: str) -> UserRole:
    membership = await get_membership_repository().find_by_tenant_and_user(
        current_tenant_id(), user_id
    )
    return membership.role if membership else UserRole.OPERATIONS


@users_router.get("", response_model=PaginatedResponse[UserListResponse])
async def list_users(
    _user: AdminDep,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedResponse[UserListResponse]:
    limit = min(max(limit, 1), 200)
    skip = max(skip, 0)
    users = await get_user_repository().find_all()
    total = len(users)
    page = users[skip : skip + limit]
    items = []
    for user in page:
        role = await _role_for_user(user.id)
        items.append(_user_list_response(user, role))
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@users_router.post("", response_model=UserListResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, _user: AdminDep) -> UserListResponse:
    if await get_user_repository().find_by_username(payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
    if await get_user_repository().find_by_email(str(payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

    phone = None
    if payload.phone:
        from src.domain.value_objects.phone import Phone

        phone = Phone(
            country_code=payload.phone.country_code,
            phone_number=payload.phone.phone_number,
        )
    user = User(
        id=new_id(),
        username=payload.username,
        email=Email(str(payload.email)),
        full_name=payload.full_name,
        phone=phone,
        password_hash=hash_password(payload.password),
        is_outsourced=payload.is_outsourced,
    )
    await get_user_repository().save(user)
    await ensure_membership(
        tenant_id=current_tenant_id(),
        user_id=user.id,
        role=payload.role,
    )
    await build_event_publisher().publish(
        UserAddedToTenant(
            tenant_id=current_tenant_id(),
            user_id=user.id,
            role=payload.role.value,
        )
    )
    return _user_list_response(user, payload.role)


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
    role = await _role_for_user(user_id)
    return _user_list_response(user, role)


@users_router.patch("/{user_id}", response_model=UserListResponse)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    _user: AdminDep,
) -> UserListResponse:
    user = await get_user_repository().find_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
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
        from src.domain.value_objects.phone import Phone

        user.phone = Phone(
            country_code=updates["phone"].country_code,
            phone_number=updates["phone"].phone_number,
        )
    if "is_outsourced" in updates:
        user.is_outsourced = updates["is_outsourced"]
    if "is_active" in updates:
        user.is_active = updates["is_active"]
    await get_user_repository().save(user)
    role = await _role_for_user(user_id)
    if "role" in updates and updates["role"] is not None:
        await ensure_membership(
            tenant_id=current_tenant_id(),
            user_id=user_id,
            role=updates["role"],
        )
        role = updates["role"]
    refreshed = await get_user_repository().find_by_id(user_id)
    return _user_list_response(refreshed or user, role)


jwks_router = APIRouter(tags=["jwks"])


@jwks_router.get("/.well-known/jwks.json")
async def jwks() -> dict:
    return build_jwks()


IDENTITY_ROUTERS = [
    health_router,
    auth_router,
    tenants_router,
    users_router,
    identity_ops_router,
    jwks_router,
]
