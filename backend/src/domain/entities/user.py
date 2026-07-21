from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.utils import now_hk
from src.domain.value_objects.phone import Phone


@dataclass
class User:
    id: str
    username: str
    email: str
    full_name: str
    password_hash: str
    phone: Optional[Phone] = None
    is_outsourced: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None

    def deactivate(self) -> None:
        self.is_active = False

    def activate(self) -> None:
        self.is_active = True

    def change_password(self, password_hash: str) -> None:
        self.password_hash = password_hash

    def update_profile(
        self,
        *,
        email: str | None = None,
        full_name: str | None = None,
        phone: Phone | None = None,
    ) -> None:
        if email is not None:
            self.email = email
        if full_name is not None:
            self.full_name = full_name
        if phone is not None:
            self.phone = phone
