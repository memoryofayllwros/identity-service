from datetime import datetime, timezone
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo
import uuid

from pydantic import BeforeValidator

HONG_KONG_TZ = ZoneInfo("Asia/Hong_Kong")


def as_hk(
    dt: datetime | None = None,
    *,
    naive_is: Literal["utc", "local"] = "utc",
) -> datetime:
    """Normalize to Hong Kong wall time.

    Naive datetimes from MongoDB are UTC components (BSON convention).
    Naive datetimes from local user input can be tagged with naive_is=\"local\".
    """
    if dt is None:
        return datetime.now(HONG_KONG_TZ)
    if dt.tzinfo is None:
        if naive_is == "local":
            return dt.replace(tzinfo=HONG_KONG_TZ)
        return dt.replace(tzinfo=timezone.utc).astimezone(HONG_KONG_TZ)
    return dt.astimezone(HONG_KONG_TZ)


def _parse_datetime_string(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=HONG_KONG_TZ)
    return parsed


def _ensure_hk_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return as_hk(value, naive_is="utc")
    if isinstance(value, str):
        return as_hk(_parse_datetime_string(value))
    raise TypeError(f"expected datetime or ISO string, got {type(value)!r}")


def _ensure_hk_datetime_optional(value: Any) -> datetime | None:
    if value is None:
        return None
    return _ensure_hk_datetime(value)


HongKongDatetime = Annotated[datetime, BeforeValidator(_ensure_hk_datetime)]
OptionalHongKongDatetime = Annotated[
    datetime | None, BeforeValidator(_ensure_hk_datetime_optional)
]


def new_id() -> str:
    """Generate a time-sortable platform ID (UUID v7)."""
    if hasattr(uuid, "uuid7"):
        return str(uuid.uuid7())
    from uuid6 import uuid7

    return str(uuid7())


def new_booking_number(on: datetime | None = None) -> str:
    """Human-readable booking number, e.g. BK-20260625-A1B2C3D4E5F6."""
    when = on or as_hk()
    token = new_id().replace("-", "")[-12:].upper()
    return f"BK-{when:%Y%m%d}-{token}"
