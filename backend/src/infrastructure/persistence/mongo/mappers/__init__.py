from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.outbox_record import OutboxRecord
from src.domain.entities.role import Role
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import TenantStatus, UserStatus
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone
from src.infrastructure.persistence.mongo.documents import (
    AuthEventDocument,
    OutboxDocument,
    RoleDocument,
    TenantDocument,
    UserDocument,
)
from src.infrastructure.persistence.mongo.embeds import MobileInfo
from src.infrastructure.persistence.mongo._utils import as_hk


class UserMapper:
    @staticmethod
    def to_domain(doc: UserDocument) -> User:
        phone = None
        if doc.phone:
            phone = Phone(
                country_code=doc.phone.country_code,
                phone_number=doc.phone.phone_number,
            )
        return User(
            id=doc.user_id,
            username=doc.username,
            email=Email(doc.email),
            full_name=doc.full_name,
            password_hash=doc.password_hash,
            phone=phone,
            position=doc.position,
            permissions=list(doc.permissions),
            must_change_password=doc.must_change_password,
            is_outsourced=doc.is_outsourced,
            status=UserStatus(doc.status),
            failed_login_count=int(doc.failed_login_count or 0),
            lockout_until=doc.lockout_until,
            last_login_at=doc.last_login_at,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    @staticmethod
    def to_document(entity: User) -> UserDocument:
        phone = None
        if entity.phone:
            phone = MobileInfo(
                country_code=entity.phone.country_code,
                phone_number=entity.phone.phone_number,
            )
        return UserDocument(
            user_id=entity.id,
            username=entity.username,
            email=entity.email.value,
            full_name=entity.full_name,
            password_hash=entity.password_hash,
            phone=phone,
            position=entity.position,
            permissions=list(entity.permissions),
            must_change_password=entity.must_change_password,
            is_outsourced=entity.is_outsourced,
            status=entity.status.value,
            failed_login_count=entity.failed_login_count,
            lockout_until=entity.lockout_until,
            last_login_at=entity.last_login_at,
            created_at=entity.created_at or as_hk(),
            updated_at=entity.updated_at,
        )


class TenantMapper:
    @staticmethod
    def to_domain(doc: TenantDocument) -> Tenant:
        return Tenant(
            id=doc.tenant_id,
            name=doc.name,
            slug=doc.slug,
            status=TenantStatus(doc.status),
            features=list(doc.features),
            is_active=doc.is_active,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            suspended_at=doc.suspended_at,
        )

    @staticmethod
    def to_document(entity: Tenant) -> TenantDocument:
        return TenantDocument(
            tenant_id=entity.id,
            name=entity.name,
            slug=entity.slug,
            status=entity.status.value,
            features=list(entity.features),
            is_active=entity.is_active,
            created_at=entity.created_at or as_hk(),
            updated_at=entity.updated_at,
            suspended_at=entity.suspended_at,
        )


class RoleMapper:
    @staticmethod
    def to_domain(doc: RoleDocument) -> Role:
        return Role(
            id=doc.role_id,
            code=doc.code,
            name=doc.name,
            permissions=list(doc.permissions),
            is_system=doc.is_system,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    @staticmethod
    def to_document(entity: Role) -> RoleDocument:
        return RoleDocument(
            role_id=entity.id,
            code=entity.code,
            name=entity.name,
            permissions=list(entity.permissions),
            is_system=entity.is_system,
            created_at=entity.created_at or as_hk(),
            updated_at=entity.updated_at,
        )


class AuthEventMapper:
    @staticmethod
    def to_domain(doc: AuthEventDocument) -> AuthEvent:
        return AuthEvent(
            id=doc.event_id,
            event_type=doc.event_type,
            user_id=doc.user_id,
            actor_user_id=doc.actor_user_id,
            detail=dict(doc.detail),
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(entity: AuthEvent) -> AuthEventDocument:
        return AuthEventDocument(
            event_id=entity.id,
            event_type=entity.event_type,
            user_id=entity.user_id,
            actor_user_id=entity.actor_user_id,
            detail=dict(entity.detail),
            created_at=entity.created_at or as_hk(),
        )


class OutboxMapper:
    @staticmethod
    def to_domain(doc: OutboxDocument) -> OutboxRecord:
        return OutboxRecord(
            id=doc.record_id,
            event_type=doc.event_type,
            payload=dict(doc.payload),
            published=doc.published,
            created_at=doc.created_at,
            published_at=doc.published_at,
        )

    @staticmethod
    def to_document(entity: OutboxRecord) -> OutboxDocument:
        return OutboxDocument(
            record_id=entity.id,
            event_type=entity.event_type,
            payload=dict(entity.payload),
            published=entity.published,
            created_at=entity.created_at or as_hk(),
            published_at=entity.published_at,
        )
