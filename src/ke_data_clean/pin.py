"""KRA PIN format validation.

Checks the shape of a Kenya Revenue Authority PIN: one letter, nine
digits, one letter -- 11 characters in total. Per KRA's own guidance
("Tax Compliance 101", kra.go.ke, September 2024), individual PINs start
with A and company PINs start with P. Other leading letters exist in
practice (for example C for partnerships in some lists); pass
``allowed_prefixes`` to widen the set.

This is a format check only. It cannot prove that a PIN exists at KRA or
that it belongs to the person named beside it.
"""

from __future__ import annotations

from ke_data_clean.result import Result

DEFAULT_ALLOWED_PREFIXES: tuple[str, ...] = ("A", "P")

_PIN_LENGTH = 11
_DIGITS = 9


def _canonicalize(raw: str) -> tuple[str, list[str]]:
    """Remove whitespace and uppercase. Return the text and the steps taken."""
    steps: list[str] = []
    without_spaces = "".join(raw.split())
    if without_spaces != raw:
        steps.append("removed spaces")
    uppercased = without_spaces.upper()
    if uppercased != without_spaces:
        steps.append("uppercased")
    return uppercased, steps


def _shape_error(pin: str, allowed: tuple[str, ...]) -> Result | None:
    """Return an invalid Result for the first shape rule broken, or None."""
    if len(pin) != _PIN_LENGTH:
        return Result(
            value=None,
            status="invalid",
            reason=f"expected {_PIN_LENGTH} characters, got {len(pin)}",
        )
    if not pin[0].isalpha():
        return Result(value=None, status="invalid", reason="first character must be a letter")
    if pin[0] not in allowed:
        return Result(
            value=None,
            status="invalid",
            reason=f"leading letter {pin[0]} is not in the allowed set {''.join(allowed)}",
        )
    if not pin[1:1 + _DIGITS].isdigit():
        return Result(
            value=None,
            status="invalid",
            reason=f"characters 2 to {_DIGITS + 1} must be digits",
        )
    if not pin[-1].isalpha():
        return Result(value=None, status="invalid", reason="last character must be a letter")
    return None


def validate(
    raw: str,
    allowed_prefixes: tuple[str, ...] = DEFAULT_ALLOWED_PREFIXES,
) -> Result:
    """Validate one KRA PIN's format.

    Args:
        raw: The PIN as found in the data.
        allowed_prefixes: Leading letters to accept. KRA documents A for
            individuals and P for companies.

    Returns:
        A Result whose value is the cleaned PIN when the status is
        "valid" or "fixed", and None otherwise. Format check only: a
        passing result does not prove the PIN exists at KRA.

    Example:
        >>> validate("a012345678b")
        Result(value='A012345678B', status='fixed', reason='uppercased')
        >>> validate("A01234567B").reason
        'expected 11 characters, got 10'
    """
    if raw is None:
        return Result(value=None, status="invalid", reason="no PIN found")
    text = str(raw)
    pin, steps = _canonicalize(text)
    if not pin:
        return Result(value=None, status="invalid", reason="no PIN found")
    shape_error = _shape_error(pin, allowed_prefixes)
    if shape_error is not None:
        return shape_error
    if steps:
        return Result(value=pin, status="fixed", reason=" and ".join(steps))
    return Result(value=pin, status="valid")


__all__ = ["DEFAULT_ALLOWED_PREFIXES", "validate"]
