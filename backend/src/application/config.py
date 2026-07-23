from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeploymentConfig:
    tenant_instance_id: str
    jwt_expire_minutes: int
