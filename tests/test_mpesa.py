"""Fixtures for the M-Pesa Details parser. All names and numbers are synthetic."""

from __future__ import annotations

import pytest

from ke_data_clean.mpesa import Parsed, parse_details

CASES = [
    (
        "Sent to Jane Wanjiku Synthetic - 254712345678",
        Parsed(kind="send", id="254712345678", name="Jane Wanjiku Synthetic", account=None),
    ),
    (
        "Sent to Grocery Store Ltd - 888880",
        Parsed(kind="send", id="888880", name="Grocery Store Ltd", account=None),
    ),
    (
        "Received from John Otieno Synthetic - 254720987654",
        Parsed(kind="receive", id="254720987654", name="John Otieno Synthetic", account=None),
    ),
    (
        "Funds Transfer to My Bank Synthetic - 1234567890",
        Parsed(kind="transfer", id="1234567890", name="My Bank Synthetic", account=None),
    ),
    (
        "Pay Bill to KPLC POSTPAID SYNTHETIC - 888880 for account 123456789",
        Parsed(kind="paybill", id="888880", name="KPLC POSTPAID SYNTHETIC", account="123456789"),
    ),
    (
        "Pay Bill to KRA SYNTHETIC - 222222 for account A012345678B",
        Parsed(kind="paybill", id="222222", name="KRA SYNTHETIC", account="A012345678B"),
    ),
    (
        "Pay Bill to County Collection SYNTHETIC - 333344",
        Parsed(kind="paybill", id="333344", name="County Collection SYNTHETIC", account=None),
    ),
    (
        "Buy Goods and Services to Supermarket SYNTHETIC - 515566",
        Parsed(kind="buy_goods", id="515566", name="Supermarket SYNTHETIC", account=None),
    ),
    (
        "Withdrawal at Agent SYNTHETIC - Agent 70000123",
        Parsed(kind="withdrawal", id="70000123", name="Agent SYNTHETIC", account=None),
    ),
    (
        "Deposit via Agent SYNTHETIC - Agent 70000456",
        Parsed(kind="deposit", id="70000456", name="Agent SYNTHETIC", account=None),
    ),
    (
        "Airtime Purchase for 254712345678",
        Parsed(kind="airtime", id="254712345678", name=None, account=None),
    ),
    (
        "Transaction Fee",
        Parsed(kind="charge", id=None, name="Transaction Fee", account=None),
    ),
    (
        "Pay Bill Charge",
        Parsed(kind="charge", id=None, name="Pay Bill Charge", account=None),
    ),
    (
        "M-Shwari Fee",
        Parsed(kind="charge", id=None, name="M-Shwari Fee", account=None),
    ),
]


@pytest.mark.parametrize(("text", "expected"), CASES)
def test_parse_details(text: str, expected: Parsed) -> None:
    assert parse_details(text) == expected


def test_extra_whitespace_is_normalized() -> None:
    result = parse_details("Sent to   Jane Wanjiku Synthetic   - 254712345678")
    assert result is not None
    assert result.name == "Jane Wanjiku Synthetic"


def test_unknown_text_returns_none_not_a_guess() -> None:
    assert parse_details("Reversal of transaction ABC123") is None
    assert parse_details("Paybill to someone - 1") is None  # id too short
    assert parse_details("") is None
    assert parse_details(None) is None  # type: ignore[arg-type]


def test_synthetic_names_stay_verbatim() -> None:
    result = parse_details("Sent to MAMA NGINA STORES SYNTH - 700112233")
    assert result is not None
    assert result.name == "MAMA NGINA STORES SYNTH"
