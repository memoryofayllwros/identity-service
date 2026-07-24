"""Dependency injection factories for FastAPI and application bootstrap."""

from __future__ import annotations

from functools import lru_cache

from src.application.commands.change_password import ChangePasswordHandler
from src.application.commands.create_user import CreateUserHandler
from src.application.commands.ensure_default_tenant import EnsureDefaultTenantHandler
from src.application.queries.user_queries import (
    GetMyPermissionsHandler,
    GetUserHandler,
    ListUsersHandler,
)
from src.application.config import DeploymentConfig
from src.application.ports.password_hasher import PasswordHasher
from src.application.ports.shared_kernel import SharedKernelPort
from src.application.ports.token_service import TokenService
from src.application.services.auth_application_service import AuthApplicationService
from src.application.services.authorization_service import AuthorizationService
from src.application.services.token_issuance_service import TokenIssuanceService
from src.domain.events.publisher import EventPublisher
from src.domain.id_generator import IDGenerator
from src.domain.unit_of_work import UnitOfWork
from src.infrastructure.messaging.event_publisher import (
    CompositeEventPublisher,
    InProcessEventPublisher,
)
from src.infrastructure.messaging.outbox_relay import OutboxRelayWorker
from src.infrastructure.messaging.redis_streams import RedisStreamsPublisher
from src.infrastructure.persistence.mongo._utils import new_id as _new_id
from src.infrastructure.persistence.mongo.repositories import (
    MongoAuthEventRepository,
    MongoOutboxRepository,
    MongoRoleRepository,
    MongoTenantRepository,
    MongoUserRepository,
)
from src.infrastructure.persistence.mongo.unit_of_work import MongoUnitOfWork
from src.infrastructure.settings import get_settings

_in_process_publisher = InProcessEventPublisher()
_event_publisher: EventPublisher | None = None
_redis_publisher: EventPublisher | None = None
_outbox_relay: OutboxRelayWorker | None = None


def get_in_process_publisher() -> InProcessEventPublisher:
    return _in_process_publisher


def build_redis_publisher() -> EventPublisher | None:
    global _redis_publisher
    if _redis_publisher is not None:
        return _redis_publisher

    settings = get_settings()
    if settings.event_transport == "redis_streams" and settings.redis_url:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        _redis_publisher = RedisStreamsPublisher(client, settings.identity_event_stream)
    return _redis_publisher


def build_event_publisher() -> EventPublisher:
    global _event_publisher
    if _event_publisher is not None:
        return _event_publisher

    redis_publisher = build_redis_publisher()
    if redis_publisher is not None:
        _event_publisher = CompositeEventPublisher(
            _in_process_publisher,
            redis_publisher,
        )
    else:
        _event_publisher = _in_process_publisher
    return _event_publisher


def build_outbox_relay_publisher() -> EventPublisher:
    redis_publisher = build_redis_publisher()
    if redis_publisher is not None:
        return CompositeEventPublisher(_in_process_publisher, redis_publisher)
    return _in_process_publisher


def reset_event_publisher() -> None:
    global _event_publisher, _redis_publisher, _outbox_relay
    _event_publisher = None
    _redis_publisher = None
    _outbox_relay = None


def get_id_generator() -> IDGenerator:
    return _new_id


def _deployment_config() -> DeploymentConfig:
    settings = get_settings()
    return DeploymentConfig(
        tenant_instance_id=settings.tenant_instance_id,
        jwt_expire_minutes=settings.jwt_expire_minutes,
    )


@lru_cache
def get_password_hasher() -> PasswordHasher:
    from src.infrastructure.security.password_hasher import BcryptPasswordHasher

    return BcryptPasswordHasher()


@lru_cache
def get_token_service() -> TokenService:
    from src.infrastructure.security.jwt_token_service import JwtTokenService

    return JwtTokenService()


@lru_cache
def get_user_repository() -> MongoUserRepository:
    return MongoUserRepository()


@lru_cache
def get_tenant_repository() -> MongoTenantRepository:
    return MongoTenantRepository()


@lru_cache
def get_role_repository() -> MongoRoleRepository:
    return MongoRoleRepository()


@lru_cache
def get_auth_event_repository() -> MongoAuthEventRepository:
    return MongoAuthEventRepository()


@lru_cache
def get_outbox_repository() -> MongoOutboxRepository:
    return MongoOutboxRepository()


@lru_cache
def get_shared_kernel() -> SharedKernelPort:
    from src.infrastructure.shared_kernel import SharedKernelAdapter

    return SharedKernelAdapter()


@lru_cache
def get_authorization_service() -> AuthorizationService:
    return AuthorizationService(
        role_repo=get_role_repository(),
        shared_kernel=get_shared_kernel(),
        id_gen=get_id_generator(),
    )


def get_unit_of_work() -> UnitOfWork:
    return MongoUnitOfWork(
        outbox_repo=get_outbox_repository(),
        id_gen=get_id_generator(),
        user_repo=get_user_repository(),
    )


def get_token_issuance_service() -> TokenIssuanceService:
    cfg = _deployment_config()
    return TokenIssuanceService(
        authz=get_authorization_service(),
        token_service=get_token_service(),
        jwt_expire_minutes=cfg.jwt_expire_minutes,
    )


def get_get_user_handler() -> GetUserHandler:
    return GetUserHandler(
        user_repo=get_user_repository(),
        authz=get_authorization_service(),
    )


def get_list_users_handler() -> ListUsersHandler:
    return ListUsersHandler(
        user_repo=get_user_repository(),
        authz=get_authorization_service(),
    )


def get_my_permissions_handler() -> GetMyPermissionsHandler:
    return GetMyPermissionsHandler(
        user_repo=get_user_repository(),
        authz=get_authorization_service(),
    )


def get_auth_application_service() -> AuthApplicationService:
    cfg = _deployment_config()
    return AuthApplicationService(
        user_repo=get_user_repository(),
        tenant_repo=get_tenant_repository(),
        authz=get_authorization_service(),
        auth_events=get_auth_event_repository(),
        jwt_expire_minutes=cfg.jwt_expire_minutes,
        id_gen=get_id_generator(),
        password_hasher=get_password_hasher(),
        token_service=get_token_service(),
        token_issuance=get_token_issuance_service(),
        get_user_handler=get_get_user_handler(),
        ensure_default_tenant_handler=get_ensure_default_tenant_handler(),
    )


def get_create_user_handler() -> CreateUserHandler:
    return CreateUserHandler(
        user_repo=get_user_repository(),
        role_repo=get_role_repository(),
        authz=get_authorization_service(),
        password_hasher=get_password_hasher(),
        uow=get_unit_of_work(),
        id_gen=get_id_generator(),
    )


def get_change_password_handler() -> ChangePasswordHandler:
    return ChangePasswordHandler(
        user_repo=get_user_repository(),
        auth_events=get_auth_event_repository(),
        password_hasher=get_password_hasher(),
        uow=get_unit_of_work(),
        id_gen=get_id_generator(),
    )


def get_outbox_relay_worker() -> OutboxRelayWorker:
    global _outbox_relay
    if _outbox_relay is None:
        _outbox_relay = OutboxRelayWorker(
            get_outbox_repository(),
            build_outbox_relay_publisher(),
        )
    return _outbox_relay


async def ensure_system_roles():
    return await get_authorization_service().ensure_system_roles()


def get_ensure_default_tenant_handler() -> EnsureDefaultTenantHandler:
    cfg = _deployment_config()
    return EnsureDefaultTenantHandler(
        tenant_repo=get_tenant_repository(),
        shared_kernel=get_shared_kernel(),
        tenant_instance_id=cfg.tenant_instance_id,
    )


async def ensure_default_tenant():
    return await get_ensure_default_tenant_handler().execute()
