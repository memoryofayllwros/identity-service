from __future__ import annotations

from dataclasses import dataclass

from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class UserRegistered(DomainEvent):
    user_id: str = ""
    mobile: str = ""  # E.164, e.g. +85246542564
