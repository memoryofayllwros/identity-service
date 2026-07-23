from __future__ import annotations

from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.invite import Invite
from src.domain.entities.membership import Membership
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.entities.role import Role
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.repositories import (
    AuthEventRepository,
    InviteRepository,
    MembershipRepository,
    OutboxRepository,
    PermissionCatalogRepository,
    RoleRepository,
    TenantRepository,
    UserRepository,
)
from src.infrastructure.persistence.mongo.documents import (
    AuthEventDocument,
    InviteDocument,
    MembershipDocument,
    OutboxDocument,
    PermissionDocument,
    RoleDocument,
    TenantDocument,
    UserDocument,
)
from src.infrastructure.persistence.mongo.mappers import (
    AuthEventMapper,
    InviteMapper,
    MembershipMapper,
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
                    "password_hash": payload.password_hash,
                    "is_outsourced": payload.is_outsourced,
                    "is_active": payload.is_active,
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
                    "plan": payload.plan,
                    "status": payload.status,
                    "features": payload.features,
                    "is_active": payload.is_active,
                    "perm_ver": payload.perm_ver,
                    "suspended_at": payload.suspended_at,
                }
            )
        else:
            await payload.insert()

    async def bump_perm_ver_for_tenant(self, tenant_id: str) -> int:
        doc = await TenantDocument.find_one(TenantDocument.tenant_id == tenant_id)
        if doc is None:
            return 1
        new_ver = int(doc.perm_ver or 1) + 1
        await doc.set({"perm_ver": new_ver})
        return new_ver


class MongoMembershipRepository(MembershipRepository):
    async def find_by_id(self, membership_id: str) -> Membership | None:
        doc = await MembershipDocument.find_one(MembershipDocument.membership_id == membership_id)
        return MembershipMapper.to_domain(doc) if doc else None

    async def find_by_tenant_and_user(
        self, tenant_id: str, user_id: str
    ) -> Membership | None:
        doc = await MembershipDocument.find_one(
            MembershipDocument.tenant_id == tenant_id,
            MembershipDocument.user_id == user_id,
        )
        return MembershipMapper.to_domain(doc) if doc else None

    async def find_active_by_user(self, user_id: str) -> Membership | None:
        doc = await MembershipDocument.find_one(
            MembershipDocument.user_id == user_id,
            MembershipDocument.is_active == True,  # noqa: E712
        )
        return MembershipMapper.to_domain(doc) if doc else None

    async def find_by_tenant(self, tenant_id: str) -> list[Membership]:
        docs = await MembershipDocument.find(MembershipDocument.tenant_id == tenant_id).to_list()
        return [MembershipMapper.to_domain(doc) for doc in docs]

    async def save(self, membership: Membership) -> None:
        existing = await MembershipDocument.find_one(
            MembershipDocument.membership_id == membership.id
        )
        payload = MembershipMapper.to_document(membership)
        if existing:
            await existing.set(
                {
                    "tenant_id": payload.tenant_id,
                    "user_id": payload.user_id,
                    "role": payload.role,
                    "role_ids": payload.role_ids,
                    "perm_ver": payload.perm_ver,
                    "is_active": payload.is_active,
                }
            )
        else:
            await payload.insert()

    async def sync_perm_ver_for_tenant(self, tenant_id: str, perm_ver: int) -> None:
        docs = await MembershipDocument.find(MembershipDocument.tenant_id == tenant_id).to_list()
        for doc in docs:
            await doc.set({"perm_ver": perm_ver})


class MongoRoleRepository(RoleRepository):
    async def find_by_id(self, role_id: str) -> Role | None:
        doc = await RoleDocument.find_one(RoleDocument.role_id == role_id)
        return RoleMapper.to_domain(doc) if doc else None

    async def find_by_ids(self, role_ids: list[str]) -> list[Role]:
        if not role_ids:
            return []
        docs = await RoleDocument.find({"role_id": {"$in": role_ids}}).to_list()
        return [RoleMapper.to_domain(doc) for doc in docs]

    async def find_platform_template(self, code: str) -> Role | None:
        doc = await RoleDocument.find_one(
            RoleDocument.tenant_id == None,  # noqa: E711
            RoleDocument.code == code,
        )
        return RoleMapper.to_domain(doc) if doc else None

    async def find_tenant_role(self, tenant_id: str, code: str) -> Role | None:
        doc = await RoleDocument.find_one(
            RoleDocument.tenant_id == tenant_id,
            RoleDocument.code == code,
        )
        return RoleMapper.to_domain(doc) if doc else None

    async def save(self, role: Role) -> None:
        existing = await RoleDocument.find_one(RoleDocument.role_id == role.id)
        payload = RoleMapper.to_document(role)
        if existing:
            await existing.set(
                {
                    "tenant_id": payload.tenant_id,
                    "code": payload.code,
                    "name": payload.name,
                    "permissions": payload.permissions,
                    "is_system": payload.is_system,
                }
            )
        else:
            await payload.insert()

    async def list_platform_templates(self) -> list[Role]:
        docs = await RoleDocument.find(RoleDocument.tenant_id == None).to_list()  # noqa: E711
        return [RoleMapper.to_domain(doc) for doc in docs]


class MongoInviteRepository(InviteRepository):
    async def find_by_id(self, invite_id: str) -> Invite | None:
        doc = await InviteDocument.find_one(InviteDocument.invite_id == invite_id)
        return InviteMapper.to_domain(doc) if doc else None

    async def find_by_token(self, token: str) -> Invite | None:
        doc = await InviteDocument.find_one(InviteDocument.token == token)
        return InviteMapper.to_domain(doc) if doc else None

    async def find_by_tenant(self, tenant_id: str) -> list[Invite]:
        docs = await InviteDocument.find(InviteDocument.tenant_id == tenant_id).to_list()
        return [InviteMapper.to_domain(doc) for doc in docs]

    async def save(self, invite: Invite) -> None:
        existing = await InviteDocument.find_one(InviteDocument.invite_id == invite.id)
        payload = InviteMapper.to_document(invite)
        if existing:
            await existing.set(
                {
                    "tenant_id": payload.tenant_id,
                    "email": payload.email,
                    "role_code": payload.role_code,
                    "token": payload.token,
                    "status": payload.status,
                    "invited_by_user_id": payload.invited_by_user_id,
                    "expires_at": payload.expires_at,
                    "accepted_at": payload.accepted_at,
                }
            )
        else:
            await payload.insert()


class MongoAuthEventRepository(AuthEventRepository):
    async def save(self, event: AuthEvent) -> None:
        await AuthEventMapper.to_document(event).insert()

    async def list_by_tenant(self, tenant_id: str, *, limit: int = 50) -> list[AuthEvent]:
        docs = (
            await AuthEventDocument.find(AuthEventDocument.tenant_id == tenant_id)
            .sort([("created_at", -1)])
            .limit(limit)
            .to_list()
        )
        return [AuthEventMapper.to_domain(doc) for doc in docs]


class MongoPermissionCatalogRepository(PermissionCatalogRepository):
    async def ensure_catalog(self, codes: list[str]) -> None:
        existing = {p.code for p in await PermissionDocument.find_all().to_list()}
        for code in codes:
            if code in existing:
                continue
            await PermissionDocument(code=code, description=code.replace(".", " ")).insert()


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
