from typing import TypeVar

from beanie import Document
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

T = TypeVar("T", bound=Document)


async def get_identity_or_404(model: type[T], field_name: str, value: str) -> T:
    """Load an Identity document or raise 404."""
    doc = await model.find_one({field_name: value})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{field_name}={value} not found",
        )
    return doc


def conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def format_duplicate_key_error(exc: DuplicateKeyError) -> str:
    details = getattr(exc, "details", None) or {}
    key_value = details.get("keyValue") or {}
    key_pattern = details.get("keyPattern") or {}

    if "booking_number" in key_pattern or "booking_number" in key_value:
        number = key_value.get("booking_number")
        if number:
            return f"Booking number {number} already exists. Please try again."
        return "Booking number already exists. Please try again."

    if key_value:
        field, value = next(iter(key_value.items()))
        return f"A record with {field}={value!r} already exists."

    return "A record with the same unique value already exists."
