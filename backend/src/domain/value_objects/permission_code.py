from __future__ import annotations

from src.domain.exceptions import DomainError

_VALID_PREFIXES = ("identity.", "tracking.", "product.", "tender.")


class PermissionCode:
    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not any(normalized.startswith(prefix) for prefix in _VALID_PREFIXES):
            raise DomainError(f"Invalid permission code: {value!r}")
        self._value = normalized

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PermissionCode) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value
