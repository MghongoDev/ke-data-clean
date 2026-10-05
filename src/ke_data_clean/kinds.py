"""The registry mapping kind names to the validator that handles each.

Both wrappers -- the pandas helper and the CLI -- dispatch through
``clean_value`` so the same rules run everywhere. A kind is a word a
caller writes in their pipeline; the registry is the single place that
ties it to a function.
"""

from __future__ import annotations

from collections.abc import Callable

from ke_data_clean import county, money, phone, pin
from ke_data_clean.result import Result

KINDS: dict[str, Callable[..., Result]] = {
    "phone": phone.normalize,
    "pin": pin.validate,
    "county": county.normalize,
    "amount": money.parse_kes,
}


def clean_value(raw: str, kind: str, **options: object) -> Result:
    """Clean one raw value with the validator registered for ``kind``.

    Args:
        raw: The value as found in the data.
        kind: One of "phone", "pin", "county", "amount".
        **options: Forwarded to the validator, for example
            ``allow_shorthand=True`` for amounts.

    Raises:
        ValueError: When the kind is not registered. The message lists
            the known kinds.
    """
    validator = KINDS.get(kind)
    if validator is None:
        known = ", ".join(sorted(KINDS))
        raise ValueError(f"unknown kind '{kind}'. Known kinds: {known}")
    return validator(raw, **options)


__all__ = ["KINDS", "clean_value"]
