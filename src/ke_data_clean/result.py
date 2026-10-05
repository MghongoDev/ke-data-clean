"""The Result contract: every validator returns value, status and reason.

Nothing is ever fixed silently. Callers decide what to do with each status.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["valid", "fixed", "invalid", "ambiguous"]


@dataclass(frozen=True)
class Result:
    """The outcome of one validation.

    Attributes:
        value: The cleaned value, or None when the input could not be cleaned.
        status: One of "valid", "fixed", "invalid", "ambiguous".
        reason: Why the status holds. Empty when the input was already valid.
    """

    value: str | None
    status: Status
    reason: str = ""
