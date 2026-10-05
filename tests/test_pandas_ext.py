"""Tests for the pandas cleaning helper."""

from __future__ import annotations

import pandas as pd
import pytest

from ke_data_clean.pandas_ext import clean_column


def test_returns_value_status_reason_columns() -> None:
    series = pd.Series(["0712 345 678", "+254712345678", "0202318463"])
    result = clean_column(series, "phone")
    assert list(result.columns) == ["value", "status", "reason"]
    assert result["value"].tolist() == ["+254712345678", "+254712345678", None]
    assert result["status"].tolist() == ["fixed", "valid", "invalid"]
    assert result.loc[2, "reason"] == "not a mobile number (landline support deferred)"


def test_index_is_preserved() -> None:
    series = pd.Series(["0712 345 678", "0712 345 678"], index=[10, 42])
    result = clean_column(series, "phone")
    assert result.index.tolist() == [10, 42]


def test_missing_values_are_invalid_not_crashes() -> None:
    series = pd.Series(["0712 345 678", None, pd.NA, float("nan")], dtype="object")
    result = clean_column(series, "phone")
    assert result["value"].tolist()[0] == "+254712345678"
    assert result.loc[1, "status"] == "invalid"
    assert result.loc[1, "reason"] == "no value found"
    assert result.loc[2, "status"] == "invalid"
    assert result.loc[3, "status"] == "invalid"


def test_duplicate_values_hit_the_cache() -> None:
    calls = []
    real = clean_column.__globals__["clean_value"]

    def counting(raw, kind, **options):
        calls.append(raw)
        return real(raw, kind, **options)

    clean_column.__globals__["clean_value"] = counting
    try:
        series = pd.Series(["0712 345 678"] * 1000)
        result = clean_column(series, "phone")
    finally:
        clean_column.__globals__["clean_value"] = real
    assert len(calls) == 1
    assert (result["status"] == "fixed").sum() == 1000


def test_options_are_forwarded() -> None:
    series = pd.Series(["KES 1,200.50", "1.2k"])
    result = clean_column(series, "amount")
    assert result.loc[1, "status"] == "invalid"
    widened = clean_column(series, "amount", allow_shorthand=True)
    assert Decimal_check(widened.loc[1, "value"])


def Decimal_check(value: str | None) -> bool:
    from decimal import Decimal

    return Decimal(value) == Decimal("1200")


def test_unknown_kind_raises_valueerror() -> None:
    with pytest.raises(ValueError, match="unknown kind"):
        clean_column(pd.Series(["x"]), "nope")


def test_input_series_is_untouched() -> None:
    series = pd.Series(["0712 345 678"])
    clean_column(series, "phone")
    assert series.tolist() == ["0712 345 678"]
