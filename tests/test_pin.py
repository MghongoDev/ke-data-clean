"""Table-driven tests for KRA PIN format validation."""

from __future__ import annotations

import pytest

from ke_data_clean.pin import validate

CASES = [
    # (input, expected value, expected status)
    # Already clean: A + 9 digits + B
    ("A012345678B", "A012345678B", "valid"),
    ("P012345678X", "P012345678X", "valid"),
    # Whitespace and case fixed
    ("  a012345678b  ", "A012345678B", "fixed"),
    ("A012345678b", "A012345678B", "fixed"),
    ("A0123 45678B", "A012345678B", "fixed"),
    ("a012345678b", "A012345678B", "fixed"),
    # Wrong leading letter (not in allowed set)
    ("Z012345678B", None, "invalid"),
    # Shape errors
    ("A01234567B", None, "invalid"),  # too short
    ("A0123456789B", None, "invalid"),  # too long
    ("0123456789B", None, "invalid"),  # starts with a digit
    ("A0123456781", None, "invalid"),  # ends with a digit
    ("A01234X678B", None, "invalid"),  # letter inside the digit block
    ("A 012345678B!", None, "invalid"),  # wrong length after cleaning
    # Empty and junk
    ("", None, "invalid"),
    ("   ", None, "invalid"),
    ("no pin here", None, "invalid"),
]


@pytest.mark.parametrize(("raw", "expected_value", "expected_status"), CASES)
def test_validate(raw: str, expected_value: str | None, expected_status: str) -> None:
    result = validate(raw)
    assert result.value == expected_value
    assert result.status == expected_status
    if expected_status == "invalid":
        assert result.reason, "invalid results must say why"


def test_leading_letter_set_is_configurable() -> None:
    assert validate("C012345678B").status == "invalid"
    result = validate("C012345678B", allowed_prefixes=("A", "P", "C"))
    assert result.status == "valid"


def test_fixed_result_says_what_changed() -> None:
    result = validate(" a012345678b ")
    assert result.status == "fixed"
    assert result.reason == "removed spaces and uppercased"


def test_none_is_invalid() -> None:
    assert validate(None).status == "invalid"  # type: ignore[arg-type]
