"""Platform permission catalog (Phase 3).

Capability-prefixed codes: tracking.*, identity.*, product.*, tender.*

Keep in sync with identity-service/backend/src/shared/permissions.py
(manual sync until shared package in Phase 2+).
See ADR-004 for sync procedure.
"""

from __future__ import annotations

# Shared-kernel version — update this string whenever the catalog changes,
# then copy this file to identity-service repo and update its pin too.
# See ADR-004 for the planned path to a proper shared package.
SHARED_KERNEL_VERSION: str = "2026-07-23"

# Identity service
IDENTITY_TENANT_ADMIN = "identity.tenant.admin"
IDENTITY_USER_ADMIN = "identity.user.admin"
IDENTITY_USER_READ = "identity.user.read"
IDENTITY_INVITE_MANAGE = "identity.invite.manage"
IDENTITY_AUDIT_READ = "identity.audit.read"

# Asset Tracking capability
TRACKING_DASHBOARD_READ = "tracking.dashboard.read"
TRACKING_DIRECTORY_READ = "tracking.directory.read"
TRACKING_PRODUCT_READ = "tracking.product.read"
TRACKING_PRODUCT_WRITE = "tracking.product.write"
TRACKING_CUSTOMER_READ = "tracking.customer.read"
TRACKING_CUSTOMER_WRITE = "tracking.customer.write"
TRACKING_LOCATION_READ = "tracking.location.read"
TRACKING_LOCATION_WRITE = "tracking.location.write"
TRACKING_KIT_READ = "tracking.kit.read"
TRACKING_KIT_WRITE = "tracking.kit.write"
TRACKING_COMPONENT_READ = "tracking.component.read"
TRACKING_COMPONENT_WRITE = "tracking.component.write"
TRACKING_COMPOSITION_WRITE = "tracking.composition.write"
TRACKING_TAG_WRITE = "tracking.tag.write"
TRACKING_BOOKING_READ = "tracking.booking.read"
TRACKING_BOOKING_WRITE = "tracking.booking.write"
TRACKING_BOOKING_WORKFLOW = "tracking.booking.workflow"
TRACKING_DN_READ = "tracking.dn.read"
TRACKING_DN_WRITE = "tracking.dn.write"
TRACKING_DN_SIGN = "tracking.dn.sign"
TRACKING_CN_READ = "tracking.cn.read"
TRACKING_CN_WRITE = "tracking.cn.write"
TRACKING_CN_SIGN = "tracking.cn.sign"
TRACKING_SCAN_EXECUTE = "tracking.scan.execute"
TRACKING_INSPECTION_WRITE = "tracking.inspection.write"
TRACKING_SNAPSHOT_WRITE = "tracking.snapshot.write"
TRACKING_ALERT_READ = "tracking.alert.read"
TRACKING_ALERT_WRITE = "tracking.alert.write"

ALL_PERMISSIONS: tuple[str, ...] = (
    IDENTITY_TENANT_ADMIN,
    IDENTITY_USER_ADMIN,
    IDENTITY_USER_READ,
    IDENTITY_INVITE_MANAGE,
    IDENTITY_AUDIT_READ,
    TRACKING_DASHBOARD_READ,
    TRACKING_DIRECTORY_READ,
    TRACKING_PRODUCT_READ,
    TRACKING_PRODUCT_WRITE,
    TRACKING_CUSTOMER_READ,
    TRACKING_CUSTOMER_WRITE,
    TRACKING_LOCATION_READ,
    TRACKING_LOCATION_WRITE,
    TRACKING_KIT_READ,
    TRACKING_KIT_WRITE,
    TRACKING_COMPONENT_READ,
    TRACKING_COMPONENT_WRITE,
    TRACKING_COMPOSITION_WRITE,
    TRACKING_TAG_WRITE,
    TRACKING_BOOKING_READ,
    TRACKING_BOOKING_WRITE,
    TRACKING_BOOKING_WORKFLOW,
    TRACKING_DN_READ,
    TRACKING_DN_WRITE,
    TRACKING_DN_SIGN,
    TRACKING_CN_READ,
    TRACKING_CN_WRITE,
    TRACKING_CN_SIGN,
    TRACKING_SCAN_EXECUTE,
    TRACKING_INSPECTION_WRITE,
    TRACKING_SNAPSHOT_WRITE,
    TRACKING_ALERT_READ,
    TRACKING_ALERT_WRITE,
)

OPERATIONS_PERMISSIONS: tuple[str, ...] = (
    IDENTITY_USER_READ,
    TRACKING_DASHBOARD_READ,
    TRACKING_DIRECTORY_READ,
    TRACKING_PRODUCT_READ,
    TRACKING_CUSTOMER_READ,
    TRACKING_LOCATION_READ,
    TRACKING_KIT_READ,
    TRACKING_KIT_WRITE,
    TRACKING_COMPONENT_READ,
    TRACKING_COMPONENT_WRITE,
    TRACKING_COMPOSITION_WRITE,
    TRACKING_TAG_WRITE,
    TRACKING_BOOKING_READ,
    TRACKING_BOOKING_WORKFLOW,
    TRACKING_DN_READ,
    TRACKING_DN_SIGN,
    TRACKING_CN_READ,
    TRACKING_CN_SIGN,
    TRACKING_SCAN_EXECUTE,
    TRACKING_INSPECTION_WRITE,
    TRACKING_SNAPSHOT_WRITE,
    TRACKING_ALERT_READ,
)

ADMIN_PERMISSIONS: tuple[str, ...] = ALL_PERMISSIONS

ROLE_CODE_ADMIN = "admin"
ROLE_CODE_OPERATIONS = "operations"

PLATFORM_ROLE_TEMPLATES: dict[str, tuple[str, ...]] = {
    ROLE_CODE_ADMIN: ADMIN_PERMISSIONS,
    ROLE_CODE_OPERATIONS: OPERATIONS_PERMISSIONS,
}

# Plan → feature flags (entitlements hooks; billing later)
PLAN_FEATURES: dict[str, list[str]] = {
    "starter": ["tracking.core"],
    "professional": ["tracking.core", "tracking.scan", "tracking.documents"],
    "enterprise": [
        "tracking.core",
        "tracking.scan",
        "tracking.documents",
        "tracking.alerts",
        "product.intel",
        "tender.intel",
    ],
}
