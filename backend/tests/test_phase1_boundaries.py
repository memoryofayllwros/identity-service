"""Phase 1 Identity boundary tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.infrastructure.persistence.mongo.documents import IDENTITY_DOCUMENT_MODELS

BACKEND_ROOT = Path(__file__).resolve().parents[1]
API_DIR = BACKEND_ROOT / "src" / "api"
SCHEMAS_DIR = BACKEND_ROOT / "src" / "schemas"
DOCUMENTS_DIR = BACKEND_ROOT / "src" / "infrastructure" / "persistence" / "mongo" / "documents"

FORBIDDEN_MODEL_SUFFIXES = (
    "booking_doc.py",
    "kit_doc.py",
    "component_doc.py",
    "product_doc.py",
    "customer_doc.py",
)

FORBIDDEN_API_FILES = (
    "bookings.py",
    "kits.py",
    "components.py",
    "products.py",
    "customers.py",
    "tracking_directory.py",
)

FORBIDDEN_SCHEMA_FILES = ("ops.py",)

APPLICATION_DIR = BACKEND_ROOT / "src" / "application"
FORBIDDEN_APPLICATION_IMPORTS = (
    "fastapi",
    "beanie",
    "motor",
    "redis",
    "infrastructure",
)

MODULES_IDENTITY_DIR = BACKEND_ROOT / "src" / "modules" / "identity"

FORBIDDEN_SHIM_INIT_FILES = (
    MODULES_IDENTITY_DIR / "models" / "__init__.py",
    MODULES_IDENTITY_DIR / "schemas" / "__init__.py",
    MODULES_IDENTITY_DIR / "security" / "__init__.py",
    MODULES_IDENTITY_DIR / "services" / "__init__.py",
)


class IdentityBoundaryTests(unittest.TestCase):
    def test_identity_models_exclude_tracking(self) -> None:
        names = {model.__name__ for model in IDENTITY_DOCUMENT_MODELS}
        for forbidden in ("CustomerDoc", "BookingDoc", "KitDoc", "ProductDoc"):
            self.assertNotIn(forbidden, names)

    def test_identity_models_include_iam(self) -> None:
        names = {model.__name__ for model in IDENTITY_DOCUMENT_MODELS}
        for required in (
            "UserDocument",
            "TenantDocument",
            "RoleDocument",
            "PermissionDocument",
            "InviteDocument",
        ):
            self.assertIn(required, names)

    def test_identity_models_count(self) -> None:
        self.assertEqual(len(IDENTITY_DOCUMENT_MODELS), 8)

    def test_models_shim_directory_removed(self) -> None:
        self.assertFalse(
            (BACKEND_ROOT / "src" / "models").exists(),
            msg="backend/src/models/ shim directory must not exist after ADR-003 migration",
        )

    def test_security_shim_directory_removed(self) -> None:
        self.assertFalse(
            (BACKEND_ROOT / "src" / "security").exists(),
            msg="backend/src/security/ shim must not exist; use infrastructure/security/",
        )

    def test_no_tracking_document_files(self) -> None:
        existing = {path.name for path in DOCUMENTS_DIR.glob("*.py")}
        for forbidden in FORBIDDEN_MODEL_SUFFIXES:
            self.assertNotIn(forbidden, existing, msg=f"tracking document still present: {forbidden}")

    def test_no_tracking_api_files(self) -> None:
        existing = {path.name for path in API_DIR.glob("*.py")}
        for forbidden in FORBIDDEN_API_FILES:
            self.assertNotIn(forbidden, existing, msg=f"tracking API still present: {forbidden}")

    def test_no_tracking_schema_files(self) -> None:
        existing = {path.name for path in SCHEMAS_DIR.glob("*.py")}
        for forbidden in FORBIDDEN_SCHEMA_FILES:
            self.assertNotIn(forbidden, existing, msg=f"tracking schema still present: {forbidden}")

    def test_no_framework_imports_in_application(self) -> None:
        for py_file in APPLICATION_DIR.rglob("*.py"):
            source = py_file.read_text()
            for forbidden in FORBIDDEN_APPLICATION_IMPORTS:
                self.assertNotIn(
                    forbidden,
                    source,
                    msg=f"{py_file.relative_to(BACKEND_ROOT)} imports forbidden '{forbidden}'",
                )

    def test_event_publisher_port_in_domain(self) -> None:
        publisher_path = BACKEND_ROOT / "src" / "domain" / "events" / "publisher.py"
        self.assertTrue(
            publisher_path.exists(),
            msg="EventPublisher port must be in domain/events/",
        )

    def test_identity_module_shims_removed(self) -> None:
        for path in FORBIDDEN_SHIM_INIT_FILES:
            self.assertFalse(
                path.exists(),
                msg=f"legacy shim {path.relative_to(BACKEND_ROOT)} must not exist; "
                f"use canonical application/ or infrastructure/ paths",
            )

    def test_shared_kernel_version_present(self) -> None:
        from src.shared.permissions import SHARED_KERNEL_VERSION

        self.assertIsInstance(SHARED_KERNEL_VERSION, str)
        self.assertRegex(
            SHARED_KERNEL_VERSION,
            r"^\d{4}-\d{2}-\d{2}$",
            msg="SHARED_KERNEL_VERSION must be an ISO date string (YYYY-MM-DD)",
        )


if __name__ == "__main__":
    unittest.main()
