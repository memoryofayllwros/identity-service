from __future__ import annotations

from dataclasses import dataclass, field

from src.domain.events.base import DomainEvent


@dataclass
class AggregateRoot:
    """
    Base for all aggregate roots.

    Rules:
    - Cross-aggregate references use IDs (str), never object references.
    - Mutations go through the aggregate root; no direct mutation of inner
      entities from outside the aggregate boundary.
    - State-changing methods append domain events to _events; the Unit of Work
      drains these after commit.
    """

    _events: list[DomainEvent] = field(
        default_factory=list, init=False, repr=False, compare=False
    )

    def collect_events(self) -> list[DomainEvent]:
        """Drain and return all pending domain events."""
        events, self._events = self._events, []
        return events

    def _record(self, event: DomainEvent) -> None:
        self._events.append(event)
