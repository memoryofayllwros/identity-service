"""Phase 1 Identity boundary tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.models import IDENTITY_DOCUMENT_MODELS

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_ROOT / "src" / "models"
API_DIR = BACKEND_ROOT / "src" / "api"

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


class IdentityBoundaryTests(unittest.TestCase):
    def test_identity_models_exclude_tracking(self) -> None:
        names = {model.__name__ for model in IDENTITY_DOCUMENT_MODELS}
        for forbidden in ("CustomerDoc", "BookingDoc", "KitDoc", "ProductDoc"):
            self.assertNotIn(forbidden, names)

    def test_identity_models_include_iam(self) -> None:
        names = {model.__name__ for model in IDENTITY_DOCUMENT_MODELS}
        for required in ("UserDoc", "TenantDoc", "RoleDoc", "PermissionDoc", "InviteDoc"):
            self.assertIn(required, names)

    def test_identity_models_count(self) -> None:
        self.assertEqual(len(IDENTITY_DOCUMENT_MODELS), 7)

    def test_no_tracking_model_files(self) -> None:
        existing = {path.name for path in MODELS_DIR.glob("*_doc.py")}
        for forbidden in FORBIDDEN_MODEL_SUFFIXES:
            self.assertNotIn(forbidden, existing, msg=f"tracking model still present: {forbidden}")

    def test_no_tracking_api_files(self) -> None:
        existing = {path.name for path in API_DIR.glob("*.py")}
        for forbidden in FORBIDDEN_API_FILES:
            self.assertNotIn(forbidden, existing, msg=f"tracking API still present: {forbidden}")


if __name__ == "__main__":
    unittest.main()
