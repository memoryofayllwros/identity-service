from src.application.ports.token_service import TokenService
from src.domain.exceptions import InvalidToken
from src.infrastructure.security.security import (
    SecurityError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)


class JwtTokenService:
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
    ) -> str:
        return create_access_token(
            subject,
            email,
            role,
            tenant_id=tenant_id,
            role_ids=role_ids,
            perm_ver=perm_ver,
            scopes=scopes,
        )

    def create_refresh_token(self, subject: str, *, tenant_id: str) -> str:
        return create_refresh_token(subject, tenant_id=tenant_id)

    def decode_refresh_token(self, token: str) -> dict:
        try:
            return decode_refresh_token(token)
        except SecurityError as exc:
            raise InvalidToken() from exc
