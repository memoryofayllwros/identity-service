from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Phone:
    country_code: str
    phone_number: str

    def digits(self) -> str:
        cc = self.country_code.strip().lstrip("+")
        return f"{cc}{self.phone_number.strip()}"
