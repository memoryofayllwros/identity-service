"""Settings for Pacific Identity Platform (Phase 1 single-tenant)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILES = (
    _REPO_ROOT / "deployment" / ".env",
    _REPO_ROOT / ".env",
)


def repo_root() -> Path:
    return _REPO_ROOT


class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    service_name: str = Field(default="identity", alias="SERVICE_NAME")
    mongodb_uri: str = Field(alias="MONGODB_URI")
    identity_database_name: str = Field(default="identity_db", alias="IDENTITY_DATABASE_NAME")
    tenant_instance_id: str = Field(alias="TENANT_INSTANCE_ID")
    deployment_id: str = Field(alias="DEPLOYMENT_ID")
    control_plane_endpoint: str | None = Field(default=None, alias="CONTROL_PLANE_ENDPOINT")
    secret_key: str = Field(alias="SECRET_KEY")
    refresh_secret_key: str = Field(alias="REFRESH_SECRET_KEY")
    jwt_algorithm: str = Field(default="RS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=7 * 24 * 60, alias="JWT_EXPIRE_MINUTES")
    jwt_private_key: str | None = Field(default=None, alias="JWT_PRIVATE_KEY")
    jwt_public_key: str | None = Field(default=None, alias="JWT_PUBLIC_KEY")
    jwt_previous_public_key: str | None = Field(default=None, alias="JWT_PREVIOUS_PUBLIC_KEY")
    domain: str | None = Field(default=None, alias="DOMAIN")
    frontend_public_url: str | None = Field(default=None, alias="FRONTEND_PUBLIC_URL")

    model_config = SettingsConfigDict(
        env_file=tuple(path for path in _ENV_FILES if path.is_file()),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    def resolved_database_name(self) -> str:
        return self.identity_database_name


def validate_deployment_tenant(settings: Settings) -> None:
    if not settings.tenant_instance_id.strip():
        raise RuntimeError("TENANT_INSTANCE_ID must be set for this deployment.")
    if not settings.deployment_id.strip():
        raise RuntimeError("DEPLOYMENT_ID must be set for this deployment.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
