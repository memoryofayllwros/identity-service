"""Beanie document models for Pacific Identity Platform."""

from src.models.auth_event_doc import AuthEventDoc
from src.models.invite_doc import InviteDoc
from src.models.membership_doc import MembershipDoc
from src.models.permission_doc import PermissionDoc
from src.models.role_doc import RoleDoc
from src.models.tenant_doc import TenantDoc
from src.models.user_doc import UserDoc

IDENTITY_DOCUMENT_MODELS = [
    TenantDoc,
    MembershipDoc,
    UserDoc,
    RoleDoc,
    PermissionDoc,
    InviteDoc,
    AuthEventDoc,
]

__all__ = [
    "IDENTITY_DOCUMENT_MODELS",
    "AuthEventDoc",
    "InviteDoc",
    "MembershipDoc",
    "PermissionDoc",
    "RoleDoc",
    "TenantDoc",
    "UserDoc",
]
