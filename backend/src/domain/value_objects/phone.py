from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Phone:
    country_code: str
    phone_number: str

    def mobile(self) -> str:
        """E.164-style mobile, e.g. +85246542564."""
        cc = self.country_code.strip().lstrip("+")
        return f"+{cc}{self.phone_number.strip()}"
