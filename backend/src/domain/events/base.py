from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any

from src.domain.utils import now_hk


@dataclass(frozen=True, slots=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=now_hk)

    @property
    def event_type(self) -> str:
        return type(self).__name__

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
        }
        for item in fields(self):
            if item.name == "occurred_at":
                continue
            payload[item.name] = getattr(self, item.name)
        return payload
