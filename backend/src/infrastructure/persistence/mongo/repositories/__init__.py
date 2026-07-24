from __future__ import annotations

from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.entities.role import Role
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.repositories import (
    AuthEventRepository,
    OutboxRepository,
    RoleRepository,
    TenantRepository,
    UserRepository,
)
from src.infrastructure.persistence.mongo.documents import (
    AuthEventDocument,
    OutboxDocument,
    RoleDocument,
    TenantDocument,
    UserDocument,
)
from src.infrastructure.persistence.mongo.mappers import (
    AuthEventMapper,
    OutboxMapper,
    RoleMapper,
    TenantMapper,
    UserMapper,
)
from src.domain.utils import now_hk


class MongoUserRepository(UserRepository):
    async def find_by_id(self, user_id: str) -> User | None:
        doc = await UserDocument.find_one(UserDocument.user_id == user_id)
        return UserMapper.to_domain(doc) if doc else None

    async def find_by_email(self, email: str) -> User | None:
        doc = await UserDocument.find_one(UserDocument.email == email)
        return UserMapper.to_domain(doc) if doc else None

    async def find_by_username(self, username: str) -> User | None:
        doc = await UserDocument.find_one(UserDocument.username == username)
        return UserMapper.to_domain(doc) if doc else None

    async def find_all(self) -> list[User]:
        docs = await UserDocument.find_all().to_list()
        return [UserMapper.to_domain(doc) for doc in docs]

    async def count(self) -> int:
        return await UserDocument.find_all().count()

    async def save(self, user: User) -> None:
        existing = await UserDocument.find_one(UserDocument.user_id == user.id)
        payload = UserMapper.to_document(user)
        if existing:
            await existing.set(
                {
                    "username": payload.username,
                    "email": payload.email,
                    "full_name": payload.full_name,
                    "phone": payload.phone,
                    "position": payload.position,
                    "password_hash": payload.password_hash,
                    "permissions": payload.permissions,
                    "must_change_password": payload.must_change_password,
                    "is_outsourced": payload.is_outsourced,
                    "status": payload.status,
                    "failed_login_count": payload.failed_login_count,
                    "lockout_until": payload.lockout_until,
                    "last_login_at": payload.last_login_at,
                    "updated_at": payload.updated_at or now_hk(),
                }
            )
        else:
            await payload.insert()


class MongoTenantRepository(TenantRepository):
    async def find_by_id(self, tenant_id: str) -> Tenant | None:
        doc = await TenantDocument.find_one(TenantDocument.tenant_id == tenant_id)
        return TenantMapper.to_domain(doc) if doc else None

    async def find_by_slug(self, slug: str) -> Tenant | None:
        doc = await TenantDocument.find_one(TenantDocument.slug == slug)
        return TenantMapper.to_domain(doc) if doc else None

    async def save(self, tenant: Tenant) -> None:
        existing = await TenantDocument.find_one(TenantDocument.tenant_id == tenant.id)
        payload = TenantMapper.to_document(tenant)
        if existing:
            await existing.set(
                {
                    "name": payload.name,
                    "slug": payload.slug,
                    "status": payload.status,
                    "features": payload.features,
                    "is_active": payload.is_active,
                    "updated_at": payload.updated_at or now_hk(),
                    "suspended_at": payload.suspended_at,
                }
            )
        else:
            await payload.insert()


class MongoRoleRepository(RoleRepository):
    async def find_by_id(self, role_id: str) -> Role | None:
        doc = await RoleDocument.find_one(RoleDocument.role_id == role_id)
        return RoleMapper.to_domain(doc) if doc else None

    async def find_by_code(self, code: str) -> Role | None:
        doc = await RoleDocument.find_one(RoleDocument.code == code)
        return RoleMapper.to_domain(doc) if doc else None

    async def find_by_ids(self, role_ids: list[str]) -> list[Role]:
        if not role_ids:
            return []
        docs = await RoleDocument.find({"role_id": {"$in": role_ids}}).to_list()
        return [RoleMapper.to_domain(doc) for doc in docs]

    async def save(self, role: Role) -> None:
        existing = await RoleDocument.find_one(RoleDocument.role_id == role.id)
        payload = RoleMapper.to_document(role)
        if existing:
            await existing.set(
                {
                    "code": payload.code,
                    "name": payload.name,
                    "permissions": payload.permissions,
                    "is_system": payload.is_system,
                    "updated_at": payload.updated_at or now_hk(),
                }
            )
        else:
            await payload.insert()

    async def list_system_roles(self) -> list[Role]:
        docs = await RoleDocument.find(RoleDocument.is_system == True).to_list()  # noqa: E712
        return [RoleMapper.to_domain(doc) for doc in docs]


class MongoAuthEventRepository(AuthEventRepository):
    async def save(self, event: AuthEvent) -> None:
        await AuthEventMapper.to_document(event).insert()

    async def list_recent(self, *, limit: int = 50) -> list[AuthEvent]:
        docs = (
            await AuthEventDocument.find_all()
            .sort([("created_at", -1)])
            .limit(limit)
            .to_list()
        )
        return [AuthEventMapper.to_domain(doc) for doc in docs]


class MongoOutboxRepository(OutboxRepository):
    async def save(self, record: OutboxRecord) -> None:
        doc = OutboxMapper.to_document(record)
        await doc.insert()

    async def find_unpublished(self, limit: int = 50) -> list[OutboxRecord]:
        docs = (
            await OutboxDocument.find(OutboxDocument.published == False)  # noqa: E712
            .sort([("created_at", 1)])
            .limit(limit)
            .to_list()
        )
        return [OutboxMapper.to_domain(doc) for doc in docs]

    async def mark_published(self, record_id: str) -> None:
        doc = await OutboxDocument.find_one(OutboxDocument.record_id == record_id)
        if doc:
            await doc.set({"published": True, "published_at": now_hk()})
