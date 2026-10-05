"""Parse the "Details" field of M-Pesa statement and B2C exports.

A Details string such as ``Pay Bill to KPLC POSTPAID - 888880 for
account 123456789`` names the kind of movement, the counterparty, its
id (phone, paybill, till or agent number) and, for paybill payments,
the account that was quoted.

``parse_details`` returns ``None`` when the text matches no known
pattern: an unrecognized Details line is reported to the caller, never
guessed. All examples use synthetic names and numbers. The pattern
grammar covers the common statement shapes; extend ``_PATTERNS`` when a
statement shows a new one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_NUMBER = r"\d{5,12}"


@dataclass(frozen=True)
class Parsed:
    """One parsed Details line.

    Attributes:
        kind: The movement type, for example "send", "paybill", "buy_goods".
        id: The counterparty number (phone, paybill, till or agent).
        name: The counterparty name as written in the statement.
        account: The account quoted on a paybill payment, if any.
    """

    kind: str
    id: str | None
    name: str | None
    account: str | None


# (compiled pattern, kind) tried in order. Each pattern is anchored, so
# order only matters where two grammars overlap by prefix.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"^Sent to (?P<name>.+?) - (?P<id>{_NUMBER})$"), "send"),
    (re.compile(rf"^Received from (?P<name>.+?) - (?P<id>{_NUMBER})$"), "receive"),
    (re.compile(rf"^Funds Transfer to (?P<name>.+?) - (?P<id>{_NUMBER})$"), "transfer"),
    (
        re.compile(
            rf"^Pay Bill to (?P<name>.+?) - (?P<id>{_NUMBER})"
            r"(?: for account (?P<account>.+))?$"
        ),
        "paybill",
    ),
    (re.compile(rf"^Buy Goods and Services to (?P<name>.+?) - (?P<id>{_NUMBER})$"), "buy_goods"),
    (re.compile(rf"^Withdrawal at (?P<name>.+?) - Agent (?P<id>{_NUMBER})$"), "withdrawal"),
    (re.compile(rf"^Deposit via (?P<name>.+?) - Agent (?P<id>{_NUMBER})$"), "deposit"),
    (re.compile(rf"^Airtime Purchase for (?P<id>{_NUMBER})$"), "airtime"),
    (
        re.compile(r"^(?P<name>Pay Bill (Charge|Commission)|Transaction Fee|M-Shwari Fee)$"),
        "charge",
    ),
]


def parse_details(text: str) -> Parsed | None:
    """Parse one M-Pesa Details string.

    Args:
        text: The Details value exactly as it appears in the statement.

    Returns:
        A Parsed with the kind, counterparty id, name and account, or
        None when the text matches no known pattern.

    Example:
        >>> parse_details("Sent to JOHN DOE - 254712345678")
        Parsed(kind='send', id='254712345678', name='JOHN DOE', account=None)
        >>> parse_details("some new wording") is None
        True
    """
    if text is None:
        return None
    collapsed = " ".join(str(text).split())
    if not collapsed:
        return None
    for pattern, kind in _PATTERNS:
        match = pattern.match(collapsed)
        if match is None:
            continue
        fields = match.groupdict()
        return Parsed(
            kind=kind,
            id=fields.get("id"),
            name=fields.get("name"),
            account=fields.get("account"),
        )
    return None


__all__ = ["Parsed", "parse_details"]
