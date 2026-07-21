from src.domain.events import (
    DomainEvent,
    InviteAccepted,
    InviteCreated,
    RoleChanged,
    TenantCreated,
    TenantSuspended,
    UserAddedToTenant,
    UserRegistered,
)
from src.infrastructure.dependencies import get_in_process_publisher
from src.infrastructure.messaging.event_publisher import InProcessEventPublisher

dispatcher: InProcessEventPublisher = get_in_process_publisher()

UserInvited = UserAddedToTenant

__all__ = [
    "DomainEvent",
    "InProcessEventPublisher",
    "InviteAccepted",
    "InviteCreated",
    "RoleChanged",
    "TenantCreated",
    "TenantSuspended",
    "UserAddedToTenant",
    "UserInvited",
    "UserRegistered",
    "dispatcher",
]
