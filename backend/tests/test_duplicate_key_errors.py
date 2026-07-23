import unittest

from pymongo.errors import DuplicateKeyError

from src.services.base import format_duplicate_key_error


class DuplicateKeyErrorFormattingTests(unittest.TestCase):
    def test_username_duplicate_message(self) -> None:
        exc = DuplicateKeyError(
            "E11000 duplicate key error",
            11000,
            {
                "keyPattern": {"username": 1},
                "keyValue": {"username": "alice"},
            },
        )
        self.assertEqual(
            format_duplicate_key_error(exc),
            "A record with username='alice' already exists.",
        )

    def test_email_duplicate_message(self) -> None:
        exc = DuplicateKeyError(
            "E11000 duplicate key error",
            11000,
            {
                "keyPattern": {"email": 1},
                "keyValue": {"email": "alice@example.com"},
            },
        )
        self.assertEqual(
            format_duplicate_key_error(exc),
            "A record with email='alice@example.com' already exists.",
        )

    def test_generic_duplicate_message(self) -> None:
        exc = DuplicateKeyError(
            "E11000 duplicate key error",
            11000,
            {
                "keyPattern": {"tenant_slug": 1},
                "keyValue": {"tenant_slug": "acme-corp"},
            },
        )
        self.assertEqual(
            format_duplicate_key_error(exc),
            "A record with tenant_slug='acme-corp' already exists.",
        )


if __name__ == "__main__":
    unittest.main()
