"""Kenyan mobile number normalization to E.164.

Rules (checked against the Communications Authority of Kenya numbering plan
as summarized on "Telephone numbers in Kenya", retrieved October 2026):

- The national significant number is 9 digits.
- The 7-series (700 to 799) is assigned to mobiles as a block.
- The 1-series (introduced in May 2019) is fragmented: only the prefixes
  listed in ``_ONE_SERIES_PREFIXES`` are assigned to mobiles. A number
  starting with 1 outside those prefixes is rejected rather than guessed.
- Landlines start with area codes 2 to 6. They are rejected with a reason;
  landline support is deferred.
- The canonical form is +254 followed by the 9-digit national number.

The prefix list reflects the Communications Authority of Kenya's
assignments as captured in Google's libphonenumber metadata for +254,
retrieved October 2026. The test suite cross-checks this against the
``phonenumbers`` package on random numbers. Re-verify against a current
CA numbering plan before relying on this in production.

Accepted input shapes (after stripping spaces, hyphens, brackets and dots):

- ``07xx`` / ``01xx``  -- national format, assumes Kenya
- ``7xx`` / ``1xx``    -- 9 digits without trunk prefix, assumes Kenya
- ``254xx...``         -- country code without +
- ``+254xx...``        -- full international format
- ``00254xx...``       -- 00 international access prefix

Verify against a current CA numbering plan before relying on this in
production.
"""

from __future__ import annotations

import re

from ke_data_clean.result import Result

DEFAULT_REGION = "KE"

_JUNK = re.compile(r"[\s\-.()\[\]]")

# Assigned 1-series mobile prefixes (first three digits), per libphonenumber
# metadata for +254 as of October 2026. The 7-series needs no list: 700 to
# 799 is assigned as a block.
_ONE_SERIES_PREFIXES = frozenset(
    [
        "100", "101", "102", "103", "104", "105", "106", "107", "108",
        "110", "111", "112", "113", "114", "115", "116", "117", "118", "119",
        "120", "121", "124", "130",
        "140", "141", "142", "143", "144", "145",
        "180", "181", "182", "183", "184", "185", "186", "187", "188", "189",
    ]
)


def _strip(raw: str) -> str:
    """Remove spaces, hyphens, brackets, dots and one leading plus."""
    return _JUNK.sub("", raw.strip()).lstrip("+")


def _to_national(cleaned: str) -> str:
    """Return the 9-digit national part, whatever shape the input had.

    Numbers with a foreign international access prefix (``00`` followed by
    something that is not 254) fall through to the local path, where they
    fail the digit checks with a clear reason.
    """
    if cleaned.startswith("00254"):
        return cleaned[5:]
    if cleaned.startswith("254"):
        return cleaned[3:]
    if cleaned.startswith("0"):
        return cleaned[1:]
    return cleaned


def _judge_national(national: str) -> Result:
    """Judge the digits after the country code: mobile, landline, or invalid."""
    if not national.isdigit():
        return Result(value=None, status="invalid", reason="contains non-digit characters")
    if len(national) != 9:
        return Result(
            value=None,
            status="invalid",
            reason=f"expected 9 digits, got {len(national)}",
        )
    first = int(national[0])
    if first == 7:
        return Result(value=f"+254{national}", status="valid")
    if first == 1:
        if national[:3] in _ONE_SERIES_PREFIXES:
            return Result(value=f"+254{national}", status="valid")
        return Result(
            value=None,
            status="invalid",
            reason=f"mobile prefix {national[:3]} is not in the assigned Kenyan ranges",
        )
    if 2 <= first <= 6:
        return Result(
            value=None,
            status="invalid",
            reason="not a mobile number (landline support deferred)",
        )
    return Result(
        value=None,
        status="invalid",
        reason=f"Kenyan mobiles start with 7 or 1, got {national[0]}",
    )


def normalize(raw: str, default_region: str = DEFAULT_REGION) -> Result:
    """Normalize one Kenyan mobile number string to E.164.

    Args:
        raw: The number as found in the data, in any common format.
        default_region: The region assumed for numbers written without a
            country code. Only "KE" is supported.

    Returns:
        A Result whose value is the E.164 number when the status is
        "valid" or "fixed", and None otherwise. A number already in
        canonical form returns status "valid"; any other accepted shape
        returns "fixed" with a reason.

    Example:
        >>> normalize("0712 345 678")
        Result(value='+254712345678', status='fixed', reason='reformatted to E.164')
        >>> normalize("020 2318463").reason
        'not a mobile number (landline support deferred)'
    """
    if raw is None:
        return Result(value=None, status="invalid", reason="empty input")
    if default_region != DEFAULT_REGION:
        return Result(
            value=None,
            status="invalid",
            reason=f"only region '{DEFAULT_REGION}' is supported",
        )
    original = str(raw).strip()
    cleaned = _strip(original)
    if not cleaned or not any(character.isdigit() for character in cleaned):
        return Result(value=None, status="invalid", reason="no digits found")
    result = _judge_national(_to_national(cleaned))
    if result.status != "valid":
        return result
    if result.value == original:
        return result
    return Result(value=result.value, status="fixed", reason="reformatted to E.164")


__all__ = ["DEFAULT_REGION", "normalize"]
