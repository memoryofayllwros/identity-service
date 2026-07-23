from __future__ import annotations

from typing import Protocol


class IDGenerator(Protocol):
    def __call__(self) -> str: ...
