"""KES amount parsing: text stored in spreadsheets into a plain number.

Handles the shapes Kenyan business data arrives in: ``KES 1,200.50``,
``Ksh. 1,200``, ``KSh1200/=``, ``1,200/-`` and plain numbers. The value
returned is the canonical decimal string; convert it with
``Decimal(result.value)`` when you need a Decimal.

Rules that refuse to guess:

- Shorthand like ``1.2k`` is rejected unless ``allow_shorthand=True``:
  in business data it is ambiguous (1.2k could be 1,200 or a typo for
  1.20), so the caller must opt in.
- Ragged thousands separators like ``1,20,0`` are rejected. The groups
  must be real: first group of 1 to 3 digits, every later group exactly
  3 digits. Otherwise the value is a guess, not a parse.
- Negative-looking amounts are rejected with a reason.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from ke_data_clean.result import Result

_CURRENCY_MARKER = re.compile(r"(?i)(kshs|ksh|kes)\.?")

_DECORATION = re.compile(r"/[=-]")

_NUMBER = re.compile(r"^\d+(\.\d+)?$")

_SHORTHAND = re.compile(r"^(?P<number>\d+(?:\.\d+)?)\s*(?P<suffix>[kKmM])$")

_SHORTHAND_MULTIPLIERS = {"k": Decimal("1000"), "m": Decimal("1000000")}


def _remove_decorations(stripped: str) -> str:
    """Remove currency words, /=, /- and a leading +. Keep digit grouping."""
    without_currency = _CURRENCY_MARKER.sub("", stripped)
    without_slash = _DECORATION.sub("", without_currency)
    return without_slash.strip().lstrip("+").strip()


def _last_group_ok(last: str) -> bool:
    """The last group is 3 digits, or 3 digits, a point, and fraction digits."""
    integer, point, fraction = last.partition(".")
    if not integer.isdigit() or len(integer) != 3:
        return False
    return point == "" or (fraction.isdigit() and fraction != "")


def _first_group_ok(first: str) -> bool:
    """The first group holds 1 to 3 digits."""
    return first.isdigit() and len(first) <= 3


def _middle_groups_ok(middles: list[str]) -> bool:
    """Every middle group is exactly 3 digits."""
    return all(len(middle) == 3 and middle.isdigit() for middle in middles)


def _split_groups(decorated: str) -> list[str] | None:
    """Split a decorated number into groups, or None when it cannot be grouped."""
    if "," not in decorated and " " not in decorated:
        return None
    if decorated.count(".") > 1:
        return None
    groups = [group for group in re.split(r"[,\s]+", decorated) if group]
    if len(groups) < 2:
        return None
    return groups


def _canonicalize_number(decorated: str) -> tuple[str | None, str]:
    """Validate separators and return the plain digit string and a failure reason."""
    if _NUMBER.match(decorated):
        return decorated, ""
    groups = _split_groups(decorated)
    if groups is None:
        return None, "not a recognizable KES amount"
    if not _first_group_ok(groups[0]):
        return None, "looks like more than one number"
    if not _middle_groups_ok(groups[1:-1]):
        return None, "irregular thousands grouping"
    if not _last_group_ok(groups[-1]):
        return None, "irregular thousands grouping"
    return "".join(groups), ""


def _reject_or_expand_shorthand(cleaned: str, allow_shorthand: bool) -> Result | None:
    """Return the Result for shorthand input, or None if it is not shorthand."""
    match = _SHORTHAND.match(cleaned)
    if match is None:
        return None
    if not allow_shorthand:
        return Result(
            value=None,
            status="invalid",
            reason=(
                "shorthand like 1.2k needs allow_shorthand=True "
                "because it is ambiguous in business data"
            ),
        )
    number = Decimal(match.group("number")) * _SHORTHAND_MULTIPLIERS[match.group("suffix").lower()]
    # The "f" format keeps plain decimal notation; str() of a normalized
    # Decimal would give 1.2E+3, which is not a canonical amount string.
    value = format(number.normalize(), "f")
    return Result(value=value, status="fixed", reason="expanded shorthand")


def parse_kes(raw: str, allow_shorthand: bool = False) -> Result:
    """Parse one KES amount string into a canonical decimal string.

    Args:
        raw: The amount as found in the data.
        allow_shorthand: Accept ``1.2k`` and ``2.5m`` style amounts.
            Off by default because shorthand is ambiguous in business data.

    Returns:
        A Result whose value is the amount as a decimal string when the
        status is "valid" or "fixed", and None otherwise.
    """
    if raw is None:
        return Result(value=None, status="invalid", reason="no amount found")
    stripped = str(raw).strip()
    if not stripped:
        return Result(value=None, status="invalid", reason="no amount found")
    if stripped.startswith(("-", "(", "−")):
        return Result(value=None, status="invalid", reason="negative amounts are rejected")
    shorthand_result = _reject_or_expand_shorthand(stripped, allow_shorthand)
    if shorthand_result is not None:
        return shorthand_result
    decorated = _remove_decorations(stripped)
    cleaned, failure_reason = _canonicalize_number(decorated)
    if cleaned is None:
        return Result(value=None, status="invalid", reason=failure_reason)
    try:
        Decimal(cleaned)
    except InvalidOperation:  # pragma: no cover - the regex checks already guarantee a parse
        return Result(value=None, status="invalid", reason="not a recognizable KES amount")
    if cleaned == stripped:
        return Result(value=cleaned, status="valid")
    return Result(value=cleaned, status="fixed", reason="parsed KES amount")


__all__ = ["parse_kes"]
