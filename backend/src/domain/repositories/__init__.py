from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.invite import Invite
from src.domain.entities.membership import Membership
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.entities.role import Role
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def find_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def find_all(self) -> list[User]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def save(self, user: User) -> None: ...


class TenantRepository(ABC):
    @abstractmethod
    async def find_by_id(self, tenant_id: str) -> Tenant | None: ...

    @abstractmethod
    async def find_by_slug(self, slug: str) -> Tenant | None: ...

    @abstractmethod
    async def save(self, tenant: Tenant) -> None: ...

    @abstractmethod
    async def bump_perm_ver_for_tenant(self, tenant_id: str) -> int: ...


class MembershipRepository(ABC):
    @abstractmethod
    async def find_by_id(self, membership_id: str) -> Membership | None: ...

    @abstractmethod
    async def find_by_tenant_and_user(
        self, tenant_id: str, user_id: str
    ) -> Membership | None: ...

    @abstractmethod
    async def find_active_by_user(self, user_id: str) -> Membership | None: ...

    @abstractmethod
    async def find_by_tenant(self, tenant_id: str) -> list[Membership]: ...

    @abstractmethod
    async def save(self, membership: Membership) -> None: ...

    @abstractmethod
    async def sync_perm_ver_for_tenant(self, tenant_id: str, perm_ver: int) -> None: ...


class RoleRepository(ABC):
    @abstractmethod
    async def find_by_id(self, role_id: str) -> Role | None: ...

    @abstractmethod
    async def find_by_ids(self, role_ids: list[str]) -> list[Role]: ...

    @abstractmethod
    async def find_platform_template(self, code: str) -> Role | None: ...

    @abstractmethod
    async def find_tenant_role(self, tenant_id: str, code: str) -> Role | None: ...

    @abstractmethod
    async def save(self, role: Role) -> None: ...

    @abstractmethod
    async def list_platform_templates(self) -> list[Role]: ...


class InviteRepository(ABC):
    @abstractmethod
    async def find_by_id(self, invite_id: str) -> Invite | None: ...

    @abstractmethod
    async def find_by_token(self, token: str) -> Invite | None: ...

    @abstractmethod
    async def find_by_tenant(self, tenant_id: str) -> list[Invite]: ...

    @abstractmethod
    async def save(self, invite: Invite) -> None: ...


class AuthEventRepository(ABC):
    @abstractmethod
    async def save(self, event: AuthEvent) -> None: ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: str, *, limit: int = 50) -> list[AuthEvent]: ...


class PermissionCatalogRepository(ABC):
    @abstractmethod
    async def ensure_catalog(self, codes: list[str]) -> None: ...


class OutboxRepository(ABC):
    @abstractmethod
    async def save(self, record: OutboxRecord) -> None: ...

    @abstractmethod
    async def find_unpublished(self, limit: int = 50) -> list[OutboxRecord]: ...

    @abstractmethod
    async def mark_published(self, record_id: str) -> None: ...
