"""Tests for the Result contract every validator must keep."""

import dataclasses

import pytest

from ke_data_clean import Result


def test_result_holds_value_status_reason() -> None:
    r = Result(value="+254712345678", status="fixed", reason="reformatted to E.164")
    assert r.value == "+254712345678"
    assert r.status == "fixed"
    assert r.reason == "reformatted to E.164"


def test_reason_defaults_to_empty() -> None:
    r = Result(value="047", status="valid")
    assert r.reason == ""


def test_result_is_frozen() -> None:
    r = Result(value=None, status="invalid", reason="letters in number")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.value = "+254712345678"  # type: ignore[misc]
