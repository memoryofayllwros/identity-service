from __future__ import annotations

import re

from src.domain.exceptions import DomainError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Email:
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        normalized = value.strip().lower()
        if not _EMAIL_RE.match(normalized):
            raise DomainError(f"Invalid email: {value!r}")
        self._value = normalized

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Email) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value
