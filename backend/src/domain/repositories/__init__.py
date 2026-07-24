from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.auth_event import AuthEvent
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


class RoleRepository(ABC):
    @abstractmethod
    async def find_by_id(self, role_id: str) -> Role | None: ...

    @abstractmethod
    async def find_by_code(self, code: str) -> Role | None: ...

    @abstractmethod
    async def find_by_ids(self, role_ids: list[str]) -> list[Role]: ...

    @abstractmethod
    async def save(self, role: Role) -> None: ...

    @abstractmethod
    async def list_system_roles(self) -> list[Role]: ...


class AuthEventRepository(ABC):
    @abstractmethod
    async def save(self, event: AuthEvent) -> None: ...

    @abstractmethod
    async def list_recent(self, *, limit: int = 50) -> list[AuthEvent]: ...


class OutboxRepository(ABC):
    @abstractmethod
    async def save(self, record: OutboxRecord) -> None: ...

    @abstractmethod
    async def find_unpublished(self, limit: int = 50) -> list[OutboxRecord]: ...

    @abstractmethod
    async def mark_published(self, record_id: str) -> None: ...
