from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.entities._base import AggregateRoot
from src.domain.enums import UserStatus
from src.domain.events import UserDeactivated, UserRegistered
from src.domain.utils import now_hk
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone


@dataclass
class User(AggregateRoot):
    id: str
    username: str
    email: Email
    full_name: str
    password_hash: str
    phone: Optional[Phone] = None
    position: str = ""
    permissions: list[str] = field(default_factory=list)
    must_change_password: bool = False
    is_outsourced: bool = False
    status: UserStatus = UserStatus.ACTIVE
    failed_login_count: int = 0
    lockout_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @classmethod
    def register(
        cls,
        *,
        user_id: str,
        username: str,
        email: Email,
        full_name: str,
        password_hash: str,
        permissions: list[str],
        phone: Phone | None = None,
        position: str = "",
        is_outsourced: bool = False,
        must_change_password: bool = False,
    ) -> User:
        user = cls(
            id=user_id,
            username=username,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            phone=phone,
            position=position,
            permissions=list(permissions),
            is_outsourced=is_outsourced,
            must_change_password=must_change_password,
            created_at=now_hk(),
        )
        user._record(
            UserRegistered(
                user_id=user_id,
                mobile=phone.mobile() if phone is not None else "",
            )
        )
        return user

    def deactivate(self) -> None:
        self.status = UserStatus.DEACTIVATED
        self.updated_at = now_hk()
        self._record(UserDeactivated(user_id=self.id))

    def suspend(self) -> None:
        self.status = UserStatus.SUSPENDED
        self.updated_at = now_hk()

    def activate(self) -> None:
        self.status = UserStatus.ACTIVE
        self.updated_at = now_hk()

    def change_password(self, password_hash: str) -> None:
        self.password_hash = password_hash
        self.must_change_password = False
        self.updated_at = now_hk()

    def record_login(self) -> None:
        self.last_login_at = now_hk()
        self.failed_login_count = 0
        self.lockout_until = None
        self.updated_at = now_hk()

    def record_failed_login(self, *, lockout_until: datetime | None = None) -> None:
        self.failed_login_count += 1
        if lockout_until is not None:
            self.lockout_until = lockout_until
        self.updated_at = now_hk()

    def update_profile(
        self,
        *,
        email: Email | None = None,
        full_name: str | None = None,
        phone: Phone | None = None,
        position: str | None = None,
    ) -> None:
        if email is not None:
            self.email = email
        if full_name is not None:
            self.full_name = full_name
        if phone is not None:
            self.phone = phone
        if position is not None:
            self.position = position
        self.updated_at = now_hk()

    def assign_permissions(self, permissions: list[str]) -> None:
        self.permissions = list(permissions)
        self.updated_at = now_hk()
