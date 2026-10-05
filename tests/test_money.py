"""Table-driven tests for KES amount parsing."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ke_data_clean.money import parse_kes

CASES = [
    # (input, expected value, expected status)
    # The guide's required shapes
    ("KES 1,200.50", "1200.50", "fixed"),
    ("Ksh. 1,200", "1200", "fixed"),
    ("KSh1200/=", "1200", "fixed"),
    ("1,200/-", "1200", "fixed"),
    ("1200.50", "1200.50", "valid"),
    ("1200", "1200", "valid"),
    # Currency marker variants
    ("Ksh 1,200/=", "1200", "fixed"),
    ("kshs.450.00", "450.00", "fixed"),
    ("KES450", "450", "fixed"),
    ("KSh 89,999.99", "89999.99", "fixed"),
    ("1 200", "1200", "fixed"),  # space as thousands separator
    ("+1200", "1200", "fixed"),
    # Leading zero preservation
    ("0.50", "0.50", "valid"),
    ("KES 0.99", "0.99", "fixed"),
    # Rejects
    ("1,200.50-450.00", None, "invalid"),  # multi-number
    ("1200 450", None, "invalid"),  # two numbers
    ("-1200", None, "invalid"),  # negative-looking
    ("(1200)", None, "invalid"),  # brackets often mean negative in accounting
    ("1.2k", None, "invalid"),  # shorthand needs opt-in
    ("2.5M", None, "invalid"),
    ("KES", None, "invalid"),  # no number
    ("", None, "invalid"),
    ("   ", None, "invalid"),
    ("abc", None, "invalid"),
    ("12.34.56", None, "invalid"),  # not one decimal number
    ("1,20,0", None, "invalid"),  # ragged grouping is not one clean number
    ("12,3456,789", None, "invalid"),  # middle group must be 3 digits
]


@pytest.mark.parametrize(("raw", "expected_value", "expected_status"), CASES)
def test_parse_kes(raw: str, expected_value: str | None, expected_status: str) -> None:
    result = parse_kes(raw)
    assert result.value == expected_value
    assert result.status == expected_status
    if expected_status == "invalid":
        assert result.reason, "invalid results must say why"


def test_shorthand_opt_in_expands() -> None:
    result = parse_kes("1.2k", allow_shorthand=True)
    assert result.status == "fixed"
    assert result.value == "1200"  # plain decimal, never 1.2E+3
    assert Decimal(result.value) == Decimal("1200")


def test_shorthand_millions_opt_in() -> None:
    result = parse_kes("2.5m", allow_shorthand=True)
    assert result.status == "fixed"
    assert result.value == "2500000"  # plain decimal, never 2.5E+6
    assert Decimal(result.value) == Decimal("2500000")


def test_value_converts_to_decimal() -> None:
    result = parse_kes("KES 1,200.50")
    assert Decimal(result.value) == Decimal("1200.50")


def test_none_is_invalid() -> None:
    assert parse_kes(None).status == "invalid"  # type: ignore[arg-type]
