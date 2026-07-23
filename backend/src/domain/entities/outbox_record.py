from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class OutboxRecord:
    """Not an aggregate — just a persistence value object for the outbox."""

    id: str
    event_type: str
    payload: dict[str, Any]
    published: bool = False
    created_at: datetime | None = None
    published_at: datetime | None = None
