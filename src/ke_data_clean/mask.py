"""Masking helpers so Kenyan personal data can be shared more safely.

Phone numbers and ID numbers are personal data under Kenya's Data
Protection Act, 2019. Mask them before sharing extracts. These helpers
keep the digits an analyst needs to spot duplicates and hide the rest.
"""

from __future__ import annotations

from ke_data_clean.phone import normalize as _normalize_phone
from ke_data_clean.result import Result


def phone(raw: str) -> Result:
    """Mask a Kenyan phone number, keeping the first 6 and last 2 digits.

    The number is normalized to E.164 first, so the masked form is
    stable across input formats: ``0712 345 678`` and ``+254-712-345-678``
    both give ``+25471*****78``. Invalid numbers return the phone
    validator's result unchanged, so the reason travels with the data.
    """
    result = _normalize_phone(raw)
    if result.value is None:
        return result
    digits = result.value
    masked = digits[:6] + "*" * (len(digits) - 8) + digits[-2:]
    return Result(value=masked, status=result.status, reason=result.reason)


def national_id(raw: str) -> Result:
    """Mask a Kenyan national ID number, keeping the first 3 and last 3 digits.

    The ID format is not verified: this is a masking helper, not a
    validator. The mask is always three stars, so it does not reveal the
    length of the ID. Fewer than 7 digits is refused: with the first and
    last 3 kept, a shorter number would stay fully readable.
    """
    if raw is None:
        return Result(value=None, status="invalid", reason="no ID number found")
    digits = "".join(character for character in str(raw) if character.isdigit())
    if not digits:
        return Result(value=None, status="invalid", reason="no ID number found")
    if len(digits) < 7:
        return Result(value=None, status="invalid", reason="too short to mask safely")
    return Result(
        value=digits[:3] + "***" + digits[-3:],
        status="fixed",
        reason="masked for sharing",
    )


__all__ = ["national_id", "phone"]
