"""Identity Platform HTTP API (auth, users, tenants, JWKS)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.models.enums import UserRole
from src.models.user_doc import UserDoc
from src.schemas.common import PaginatedResponse
from src.schemas.reference import UserCreate, UserDirectoryEntry, UserListResponse, UserUpdate
from src.security.dependencies import require_permission
from src.security.jwt_keys import build_jwks
from src.security.principal import Principal
from src.security.security import hash_password
from src.services.auth_service import ensure_membership
from src.services.base import get_identity_or_404
from src.shared.events import UserAddedToTenant, dispatcher
from src.shared.permissions import IDENTITY_USER_ADMIN, IDENTITY_USER_READ
from src.shared.tenant_context import current_tenant_id

# Re-export routers composed in identity_main
from src.api.auth import router as auth_router
from src.api.health import router as health_router
from src.api.identity_ops import router as identity_ops_router
from src.modules.identity.api.tenants import router as tenants_router

users_router = APIRouter(prefix="/users", tags=["users"])
AdminDep = Annotated[Principal, Depends(require_permission(IDENTITY_USER_ADMIN))]
ReadDep = Annotated[Principal, Depends(require_permission(IDENTITY_USER_READ, IDENTITY_USER_ADMIN))]


@users_router.get("", response_model=PaginatedResponse[UserListResponse])
async def list_users(
    _user: AdminDep,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedResponse[UserListResponse]:
    limit = min(max(limit, 1), 200)
    skip = max(skip, 0)
    query = UserDoc.find_all()
    total = await query.count()
    items = await query.skip(skip).limit(limit).to_list()
    return PaginatedResponse(
        items=[UserListResponse.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@users_router.post("", response_model=UserListResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, _user: AdminDep) -> UserListResponse:
    if await UserDoc.find_one(UserDoc.username == payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
    if await UserDoc.find_one(UserDoc.email == payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")

    doc = UserDoc(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_outsourced=payload.is_outsourced,
    )
    await doc.insert()
    await ensure_membership(
        tenant_id=current_tenant_id(),
        user_id=doc.user_id,
        role=payload.role,
    )
    await dispatcher.publish(
        UserAddedToTenant(
            tenant_id=current_tenant_id(),
            user_id=doc.user_id,
            role=payload.role.value,
        )
    )
    return UserListResponse.model_validate(doc)


@users_router.get("/by-ids", response_model=list[UserDirectoryEntry])
async def get_users_by_ids(
    _user: ReadDep,
    ids: str = Query(..., min_length=1, description="Comma-separated user IDs"),
) -> list[UserDirectoryEntry]:
    requested = [part.strip() for part in ids.split(",") if part.strip()][:50]
    if not requested:
        return []
    users = await UserDoc.find({"user_id": {"$in": requested}}).to_list()
    by_id = {u.user_id: u for u in users}
    return [UserDirectoryEntry.model_validate(by_id[i]) for i in requested if i in by_id]


@users_router.get("/{user_id}", response_model=UserListResponse)
async def get_user(user_id: str, _user: ReadDep) -> UserListResponse:
    doc = await get_identity_or_404(UserDoc, "user_id", user_id)
    return UserListResponse.model_validate(doc)


@users_router.patch("/{user_id}", response_model=UserListResponse)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    _user: AdminDep,
) -> UserListResponse:
    doc = await get_identity_or_404(UserDoc, "user_id", user_id)
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        existing = await UserDoc.find_one(UserDoc.email == updates["email"])
        if existing and existing.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists.")
    if updates:
        await doc.set(updates)
        if "role" in updates:
            await ensure_membership(
                tenant_id=current_tenant_id(),
                user_id=user_id,
                role=updates["role"],
            )
    return UserListResponse.model_validate(await get_identity_or_404(UserDoc, "user_id", user_id))


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
