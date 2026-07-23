from src.domain.entities.auth_event import AuthEvent
from src.domain.entities.invite import Invite
from src.domain.entities.membership import Membership
from src.domain.entities.role import Role
from src.domain.entities.tenant import Tenant
from src.domain.entities.user import User
from src.domain.enums import InviteStatus, TenantStatus, UserRole
from src.domain.value_objects.email import Email
from src.domain.value_objects.phone import Phone
from src.infrastructure.persistence.mongo.documents import (
    AuthEventDocument,
    InviteDocument,
    MembershipDocument,
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
            is_outsourced=doc.is_outsourced,
            is_active=doc.is_active,
            created_at=doc.created_at,
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
            is_outsourced=entity.is_outsourced,
            is_active=entity.is_active,
            created_at=entity.created_at or as_hk(),
        )


class TenantMapper:
    @staticmethod
    def to_domain(doc: TenantDocument) -> Tenant:
        return Tenant(
            id=doc.tenant_id,
            name=doc.name,
            slug=doc.slug,
            plan=doc.plan,
            status=TenantStatus(doc.status),
            features=list(doc.features),
            is_active=doc.is_active,
            perm_ver=int(doc.perm_ver or 1),
            created_at=doc.created_at,
            suspended_at=doc.suspended_at,
        )

    @staticmethod
    def to_document(entity: Tenant) -> TenantDocument:
        return TenantDocument(
            tenant_id=entity.id,
            name=entity.name,
            slug=entity.slug,
            plan=entity.plan,
            status=entity.status,
            features=list(entity.features),
            is_active=entity.is_active,
            perm_ver=entity.perm_ver,
            created_at=entity.created_at or as_hk(),
            suspended_at=entity.suspended_at,
        )


class MembershipMapper:
    @staticmethod
    def to_domain(doc: MembershipDocument) -> Membership:
        return Membership(
            id=doc.membership_id,
            tenant_id=doc.tenant_id,
            user_id=doc.user_id,
            role=doc.role,
            role_ids=list(doc.role_ids),
            perm_ver=int(doc.perm_ver or 1),
            is_active=doc.is_active,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(entity: Membership) -> MembershipDocument:
        return MembershipDocument(
            membership_id=entity.id,
            tenant_id=entity.tenant_id,
            user_id=entity.user_id,
            role=entity.role,
            role_ids=list(entity.role_ids),
            perm_ver=entity.perm_ver,
            is_active=entity.is_active,
            created_at=entity.created_at or as_hk(),
        )


class RoleMapper:
    @staticmethod
    def to_domain(doc: RoleDocument) -> Role:
        return Role(
            id=doc.role_id,
            code=doc.code,
            name=doc.name,
            permissions=list(doc.permissions),
            tenant_id=doc.tenant_id,
            is_system=doc.is_system,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(entity: Role) -> RoleDocument:
        return RoleDocument(
            role_id=entity.id,
            code=entity.code,
            name=entity.name,
            permissions=list(entity.permissions),
            tenant_id=entity.tenant_id,
            is_system=entity.is_system,
            created_at=entity.created_at or as_hk(),
        )


class InviteMapper:
    @staticmethod
    def to_domain(doc: InviteDocument) -> Invite:
        return Invite(
            id=doc.invite_id,
            tenant_id=doc.tenant_id,
            email=Email(doc.email),
            token=doc.token,
            expires_at=doc.expires_at,
            role_code=doc.role_code,
            status=InviteStatus(doc.status),
            invited_by_user_id=doc.invited_by_user_id,
            accepted_at=doc.accepted_at,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(entity: Invite) -> InviteDocument:
        return InviteDocument(
            invite_id=entity.id,
            tenant_id=entity.tenant_id,
            email=str(entity.email),
            token=entity.token,
            expires_at=entity.expires_at,
            role_code=entity.role_code,
            status=entity.status,
            invited_by_user_id=entity.invited_by_user_id,
            accepted_at=entity.accepted_at,
            created_at=entity.created_at or as_hk(),
        )


class AuthEventMapper:
    @staticmethod
    def to_domain(doc: AuthEventDocument) -> AuthEvent:
        return AuthEvent(
            id=doc.event_id,
            event_type=doc.event_type,
            tenant_id=doc.tenant_id,
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
            tenant_id=entity.tenant_id,
            user_id=entity.user_id,
            actor_user_id=entity.actor_user_id,
            detail=dict(entity.detail),
            created_at=entity.created_at or as_hk(),
        )
