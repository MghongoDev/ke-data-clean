"""Tests for the masking helpers."""

from __future__ import annotations

import pytest

from ke_data_clean.mask import national_id, phone

PHONE_CASES = [
    ("0712 345 678", "+25471*****78"),
    ("+254-712-345-678", "+25471*****78"),  # same digits, same mask
    ("712345678", "+25471*****78"),
    ("+254712345678", "+25471*****78"),
    ("0110987654", "+25411*****54"),
]

ID_CASES = [
    ("12345678", "123***678"),
    ("1234567", "123***567"),
    ("123456789", "123***789"),
    ("12 345 678", "123***678"),
    (" 12345678 ", "123***678"),
]


def test_id_mask_hides_length() -> None:
    eight = national_id("12345678").value
    nine = national_id("123456789").value
    assert eight == "123***678"
    assert nine == "123***789"  # same mask width regardless of input length
    assert national_id("1234567").value == "123***567"


@pytest.mark.parametrize(("raw", "expected"), PHONE_CASES)
def test_phone_mask(raw: str, expected: str) -> None:
    result = phone(raw)
    assert result.value == expected
    assert result.status in ("valid", "fixed")


def test_phone_mask_passes_invalid_through_with_reason() -> None:
    result = phone("0202318463")
    assert result.status == "invalid"
    assert "landline" in result.reason


def test_phone_mask_keeps_digit_count() -> None:
    masked = phone("0712345678").value
    assert len(masked) == len("+254712345678")
    assert masked.count("*") == 3


@pytest.mark.parametrize(("raw", "expected"), ID_CASES)
def test_national_id_mask(raw: str, expected: str) -> None:
    assert national_id(raw).value == expected


def test_national_id_too_short_is_invalid() -> None:
    result = national_id("123")
    assert result.status == "invalid"
    assert result.value is None


def test_national_id_empty_is_invalid() -> None:
    assert national_id("").status == "invalid"
    assert national_id(None).status == "invalid"  # type: ignore[arg-type]
