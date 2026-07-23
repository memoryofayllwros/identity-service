from __future__ import annotations

from typing import Protocol


class TokenService(Protocol):
    def create_access_token(
        self,
        subject: str,
        email: str,
        role: str,
        *,
        tenant_id: str,
        role_ids: list[str] | None = None,
        perm_ver: int = 1,
        scopes: list[str] | None = None,
    ) -> str: ...

    def create_refresh_token(self, subject: str, *, tenant_id: str) -> str: ...

    def decode_refresh_token(self, token: str) -> dict: ...
