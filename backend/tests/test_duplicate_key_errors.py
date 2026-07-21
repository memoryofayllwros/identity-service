import unittest

from pymongo.errors import DuplicateKeyError

from src.services.base import format_duplicate_key_error


class DuplicateKeyErrorFormattingTests(unittest.TestCase):
    def test_booking_number_duplicate_message(self) -> None:
        exc = DuplicateKeyError(
            'E11000 duplicate key error collection: bookings index: booking_number_1 '
            'dup key: { booking_number: "BK-20260629-019F1291" }',
            11000,
            {
                "keyPattern": {"booking_number": 1},
                "keyValue": {"booking_number": "BK-20260629-019F1291"},
            },
        )
        self.assertEqual(
            format_duplicate_key_error(exc),
            "Booking number BK-20260629-019F1291 already exists. Please try again.",
        )

    def test_generic_duplicate_message(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
