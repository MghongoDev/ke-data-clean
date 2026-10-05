"""Dev-only cross-check: our phone judgment against the phonenumbers library.

The guide requires that a loop of randomly generated numbers agrees with
phonenumbers on valid versus invalid for Kenyan mobiles. We compare
"accepted by ke-data-clean" against "phonenumbers classifies the parsed
number as a valid Kenyan mobile". Skipped when phonenumbers is not
installed.
"""

from __future__ import annotations

import random

import pytest

from ke_data_clean.phone import normalize

phonenumbers = pytest.importorskip("phonenumbers")

from phonenumbers import PhoneNumberType, is_valid_number, number_type, parse  # noqa: E402

SEED = 42
ITERATIONS = 2000


def _random_national(rng: random.Random) -> str:
    return "".join(str(rng.randint(0, 9)) for _ in range(9))


def _random_shape(rng: random.Random) -> str:
    national = _random_national(rng)
    shape = rng.choice(["national", "international", "bare"])
    if shape == "national":
        return "0" + national
    if shape == "international":
        return "+254" + national
    return national


def _is_mobile_per_phonenumbers(raw: str) -> bool:
    try:
        parsed = parse(raw, "KE")
    except phonenumbers.NumberParseException:
        return False
    return is_valid_number(parsed) and number_type(parsed) in (
        PhoneNumberType.MOBILE,
        PhoneNumberType.FIXED_LINE_OR_MOBILE,
    )


def test_random_numbers_agree_with_phonenumbers() -> None:
    rng = random.Random(SEED)
    mismatches: list[tuple[str, str, bool]] = []
    for _ in range(ITERATIONS):
        raw = _random_shape(rng)
        our_result = normalize(raw)
        ours = our_result.status in ("valid", "fixed")
        theirs = _is_mobile_per_phonenumbers(raw)
        if ours != theirs:
            mismatches.append((raw, our_result.status, theirs))
    assert not mismatches, f"{len(mismatches)} mismatches, first 10: {mismatches[:10]}"


def test_accepted_values_match_phonenumbers_e164() -> None:
    """When we accept a number, the E.164 value must be the canonical one."""
    rng = random.Random(SEED + 1)
    for _ in range(ITERATIONS):
        raw = _random_shape(rng)
        result = normalize(raw)
        if result.status not in ("valid", "fixed"):
            continue
        parsed = parse(raw, "KE")
        assert result.value == "+" + str(parsed.country_code) + str(parsed.national_number)
