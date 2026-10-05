"""Table-driven tests for phone normalization.

At least 30 cases per the implementation guide, including the edge cases
it names: too long, too short, letter O instead of zero, landline, and
the shapes the module accepts.
"""

from __future__ import annotations

import pytest

from ke_data_clean.phone import normalize

CASES = [
    # (input, expected value, expected status)
    # National format, 07xx and 01xx
    ("0712 345 678", "+254712345678", "fixed"),
    ("0712-345-678", "+254712345678", "fixed"),
    ("0712.345.678", "+254712345678", "fixed"),
    ("0712345678", "+254712345678", "fixed"),
    ("0722333444", "+254722333444", "fixed"),
    ("0799888777", "+254799888777", "fixed"),
    ("0110 987 654", "+254110987654", "fixed"),
    ("0119988776", "+254119988776", "fixed"),
    ("0180988776", "+254180988776", "fixed"),
    # Assigned 1-series boundaries: 130 assigned, 131 not, 122 not, 123 not
    ("0130988776", "+254130988776", "fixed"),
    ("0131988776", None, "invalid"),
    ("0122988776", None, "invalid"),
    ("0123988776", None, "invalid"),
    # National format with brackets and extra spacing
    ("(0712) 345-678", "+254712345678", "fixed"),
    # Without trunk 0, 9 digits starting 7 or 1
    ("712345678", "+254712345678", "fixed"),
    ("110987654", "+254110987654", "fixed"),
    # International shapes
    ("+254712345678", "+254712345678", "valid"),
    ("+254 712 345 678", "+254712345678", "fixed"),
    ("+254-712-345-678", "+254712345678", "fixed"),
    ("254712345678", "+254712345678", "fixed"),
    ("00254712345678", "+254712345678", "fixed"),
    ("+254712 345 678.", "+254712345678", "fixed"),
    # Wrong length
    ("07123456789", None, "invalid"),  # too long
    ("0712 34", None, "invalid"),  # too short
    ("71234567", None, "invalid"),  # 8 digits
    ("+2547123456789", None, "invalid"),  # 10 digits after 254
    ("0712", None, "invalid"),
    # Letter O instead of zero, letters in general
    ("O712345678", None, "invalid"),
    ("07123O5678", None, "invalid"),
    ("phone number", None, "invalid"),
    # Empty and whitespace
    ("", None, "invalid"),
    ("   ", None, "invalid"),
    # Landlines: area codes 2 to 6
    ("0202318463", None, "invalid"),  # Nairobi landline
    ("+25451556677", None, "invalid"),  # Nakuru landline via 254
    ("0612031444", None, "invalid"),  # Nyeri landline
    # Leading digits that are not an assigned Kenyan mobile prefix
    ("0301234567", None, "invalid"),
    ("0812345678", None, "invalid"),
    ("0912345678", None, "invalid"),
    ("0501234567", None, "invalid"),
    ("0159123456", None, "invalid"),  # 159 unassigned in the 1-series
]


@pytest.mark.parametrize(("raw", "expected_value", "expected_status"), CASES)
def test_normalize(raw: str, expected_value: str | None, expected_status: str) -> None:
    result = normalize(raw)
    assert result.value == expected_value
    assert result.status == expected_status
    if expected_status == "invalid":
        assert result.reason, "invalid results must say why"


def test_valid_canonical_input_has_no_reason() -> None:
    result = normalize("+254712345678")
    assert result.status == "valid"
    assert result.reason == ""


def test_fixed_result_carries_reason() -> None:
    result = normalize("0712 345 678")
    assert result.status == "fixed"
    assert result.reason == "reformatted to E.164"


def test_none_input_is_invalid() -> None:
    result = normalize(None)  # type: ignore[arg-type]
    assert result.status == "invalid"
    assert result.reason == "empty input"


def test_unsupported_region_is_rejected() -> None:
    result = normalize("0712345678", default_region="UG")
    assert result.status == "invalid"
    assert "region" in result.reason


@pytest.mark.parametrize("raw", ["0474 123 456", "0666123456"])
def test_area_code_range_boundaries_are_landlines(raw: str) -> None:
    assert normalize(raw).reason == "not a mobile number (landline support deferred)"
