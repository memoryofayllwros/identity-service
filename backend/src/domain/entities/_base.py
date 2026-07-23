from __future__ import annotations


class AggregateRoot:
    """
    Marker base class for aggregate roots.

    Rules:
    - Cross-aggregate references use IDs (str), never object references.
    - Mutations go through the aggregate root; no direct mutation of inner
      entities from outside the aggregate boundary.
    """
