"""Dependency injection factories for FastAPI and application bootstrap."""

from __future__ import annotations

from functools import lru_cache

from src.application.commands.accept_invite import AcceptInviteHandler
from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler
from src.application.commands.invite_user import InviteUserHandler
from src.application.commands.suspend_tenant import ActivateTenantHandler, SuspendTenantHandler
from src.application.services.auth_application_service import AuthApplicationService
from src.application.services.authorization_service import AuthorizationService
from src.application.services.membership_service import MembershipService
from src.infrastructure.messaging.event_publisher import (
    CompositeEventPublisher,
    EventPublisher,
    InProcessEventPublisher,
)
from src.infrastructure.messaging.redis_streams import RedisStreamsPublisher
from src.infrastructure.persistence.mongo.repositories import (
    MongoAuthEventRepository,
    MongoInviteRepository,
    MongoMembershipRepository,
    MongoPermissionCatalogRepository,
    MongoRoleRepository,
    MongoTenantRepository,
    MongoUserRepository,
)
from src.infrastructure.settings import get_settings

_in_process_publisher = InProcessEventPublisher()
_event_publisher: EventPublisher | None = None


def get_in_process_publisher() -> InProcessEventPublisher:
    return _in_process_publisher


def build_event_publisher() -> EventPublisher:
    global _event_publisher
    if _event_publisher is not None:
        return _event_publisher

    settings = get_settings()
    if settings.event_transport == "redis_streams" and settings.redis_url:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        _event_publisher = CompositeEventPublisher(
            _in_process_publisher,
            RedisStreamsPublisher(client, settings.identity_event_stream),
        )
    else:
        _event_publisher = _in_process_publisher
    return _event_publisher


def reset_event_publisher() -> None:
    global _event_publisher
    _event_publisher = None


@lru_cache
def get_user_repository() -> MongoUserRepository:
    return MongoUserRepository()


@lru_cache
def get_tenant_repository() -> MongoTenantRepository:
    return MongoTenantRepository()


@lru_cache
def get_membership_repository() -> MongoMembershipRepository:
    return MongoMembershipRepository()


@lru_cache
def get_role_repository() -> MongoRoleRepository:
    return MongoRoleRepository()


@lru_cache
def get_invite_repository() -> MongoInviteRepository:
    return MongoInviteRepository()


@lru_cache
def get_auth_event_repository() -> MongoAuthEventRepository:
    return MongoAuthEventRepository()


@lru_cache
def get_permission_catalog_repository() -> MongoPermissionCatalogRepository:
    return MongoPermissionCatalogRepository()


@lru_cache
def get_authorization_service() -> AuthorizationService:
    return AuthorizationService(
        role_repo=get_role_repository(),
        membership_repo=get_membership_repository(),
        tenant_repo=get_tenant_repository(),
        permission_catalog_repo=get_permission_catalog_repository(),
    )


def get_membership_service() -> MembershipService:
    return MembershipService(
        membership_repo=get_membership_repository(),
        tenant_repo=get_tenant_repository(),
        authz=get_authorization_service(),
        publisher=build_event_publisher(),
    )


def get_auth_application_service() -> AuthApplicationService:
    settings = get_settings()
    return AuthApplicationService(
        user_repo=get_user_repository(),
        tenant_repo=get_tenant_repository(),
        membership_service=get_membership_service(),
        authz=get_authorization_service(),
        auth_events=get_auth_event_repository(),
        default_tenant_id=settings.tenant_instance_id,
    )


def get_invite_user_handler() -> InviteUserHandler:
    return InviteUserHandler(
        tenant_repo=get_tenant_repository(),
        invite_repo=get_invite_repository(),
        authz=get_authorization_service(),
        auth_events=get_auth_event_repository(),
        publisher=build_event_publisher(),
    )


def get_accept_invite_handler() -> AcceptInviteHandler:
    return AcceptInviteHandler(
        invite_repo=get_invite_repository(),
        tenant_repo=get_tenant_repository(),
        user_repo=get_user_repository(),
        membership_repo=get_membership_repository(),
        authz=get_authorization_service(),
        auth_events=get_auth_event_repository(),
        publisher=build_event_publisher(),
        membership_service=get_membership_service(),
    )


def get_suspend_tenant_handler() -> SuspendTenantHandler:
    return SuspendTenantHandler(
        tenant_repo=get_tenant_repository(),
        authz=get_authorization_service(),
        auth_events=get_auth_event_repository(),
        publisher=build_event_publisher(),
    )


def get_activate_tenant_handler() -> ActivateTenantHandler:
    return ActivateTenantHandler(
        tenant_repo=get_tenant_repository(),
        authz=get_authorization_service(),
        auth_events=get_auth_event_repository(),
        publisher=build_event_publisher(),
    )


def get_ensure_default_tenant_handler() -> EnsureDefaultTenantHandler:
    return EnsureDefaultTenantHandler(
        tenant_repo=get_tenant_repository(),
        authz=get_authorization_service(),
        publisher=build_event_publisher(),
    )


def get_register_tenant_handler():
    from src.application.commands.register_tenant import RegisterTenantHandler

    return RegisterTenantHandler(
        tenant_repo=get_tenant_repository(),
        user_repo=get_user_repository(),
        membership_service=get_membership_service(),
        authz=get_authorization_service(),
        auth_events=get_auth_event_repository(),
        publisher=build_event_publisher(),
        auth_app=get_auth_application_service(),
    )


async def ensure_default_tenant():
    return await get_ensure_default_tenant_handler().execute()


async def ensure_platform_role_templates():
    return await get_authorization_service().ensure_platform_role_templates()


async def ensure_membership(*, tenant_id: str, user_id: str, role):
    from src.domain.enums import UserRole

    if not isinstance(role, UserRole):
        role = UserRole(role)
    return await get_membership_service().ensure_membership(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
    )
