from datetime import datetime, timezone
from zoneinfo import ZoneInfo

HONG_KONG_TZ = ZoneInfo("Asia/Hong_Kong")


def now_hk() -> datetime:
    return datetime.now(HONG_KONG_TZ)
