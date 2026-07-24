from __future__ import annotations

from src.application.ports.shared_kernel import SharedKernelPort
from src.shared.constants import DEFAULT_TENANT_NAME, DEFAULT_TENANT_SLUG
from src.shared.permissions import (
    ALL_PERMISSIONS,
    IDENTITY_INVITE_MANAGE,
    IDENTITY_TENANT_ADMIN,
    IDENTITY_USER_ADMIN,
    PLAN_FEATURES,
    PLATFORM_ROLE_TEMPLATES,
    ROLE_CODE_ADMIN,
    ROLE_CODE_OPERATIONS,
)


class SharedKernelAdapter(SharedKernelPort):
    """Infrastructure adapter for the manually-synced shared kernel (ADR-004)."""

    def all_permissions(self) -> tuple[str, ...]:
        return tuple(ALL_PERMISSIONS)

    def platform_role_templates(self) -> dict[str, tuple[str, ...]]:
        return {code: tuple(perms) for code, perms in PLATFORM_ROLE_TEMPLATES.items()}

    def plan_features(self, plan: str) -> tuple[str, ...]:
        return tuple(PLAN_FEATURES.get(plan, PLAN_FEATURES["starter"]))

    def known_plans(self) -> frozenset[str]:
        return frozenset(PLAN_FEATURES.keys())

    @property
    def role_code_admin(self) -> str:
        return ROLE_CODE_ADMIN

    @property
    def role_code_operations(self) -> str:
        return ROLE_CODE_OPERATIONS

    @property
    def identity_tenant_admin(self) -> str:
        return IDENTITY_TENANT_ADMIN

    @property
    def identity_user_admin(self) -> str:
        return IDENTITY_USER_ADMIN

    @property
    def identity_invite_manage(self) -> str:
        return IDENTITY_INVITE_MANAGE

    @property
    def default_tenant_name(self) -> str:
        return DEFAULT_TENANT_NAME

    @property
    def default_tenant_slug(self) -> str:
        return DEFAULT_TENANT_SLUG
