"""Beanie document models — compatibility shims (see infrastructure/persistence/mongo/documents)."""

from src.infrastructure.persistence.mongo.documents import (
    IDENTITY_DOCUMENT_MODELS,
    AuthEventDocument,
    InviteDocument,
    MembershipDocument,
    PermissionDocument,
    RoleDocument,
    TenantDocument,
    UserDocument,
)

AuthEventDoc = AuthEventDocument
InviteDoc = InviteDocument
MembershipDoc = MembershipDocument
PermissionDoc = PermissionDocument
RoleDoc = RoleDocument
TenantDoc = TenantDocument
UserDoc = UserDocument

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
