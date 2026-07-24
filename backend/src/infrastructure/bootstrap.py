"""Wire cross-cutting runtime context from deployment settings."""

from __future__ import annotations

from src.infrastructure.settings import get_settings
from src.shared.tenant_context import configure_deployment_tenant_id


def bootstrap_tenant_context() -> None:
    configure_deployment_tenant_id(get_settings().tenant_instance_id)
