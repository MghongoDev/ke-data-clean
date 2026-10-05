"""County name and code normalization for all 47 counties of Kenya.

The data lives in ``data/counties.csv`` (code, name) and follows the
First Schedule of the Constitution of Kenya (2010): code 001 is Mombasa
and code 047 is Nairobi. Names are the official spellings with spaces
instead of hyphens or apostrophes except where the apostrophe is part of
the name (Murang'a).

Normalization steps: lowercase, strip apostrophes, hyphens and the word
"county", then exact alias lookup, then fuzzy matching with
``difflib.get_close_matches``. When two or more candidates are equally
close, the result is ``ambiguous``: the tool refuses to guess.
"""

from __future__ import annotations

import csv
import difflib
import importlib.resources
from functools import lru_cache

from ke_data_clean.result import Result

_FUZZY_CUTOFF = 0.75

_COUNTY_WORD = "county"


@lru_cache(maxsize=1)
def _load_rows() -> tuple[tuple[str, str], ...]:
    """Read counties.csv once and return (code, name) pairs."""
    resource = importlib.resources.files("ke_data_clean.data").joinpath("counties.csv")
    with resource.open(newline="", encoding="utf-8") as handle:
        return tuple((row["code"], row["name"]) for row in csv.DictReader(handle))


def _code_of(name: str) -> str:
    for code, official in _load_rows():
        if official == name:
            return code
    raise KeyError(name)  # pragma: no cover - every name in ALIASES comes from the file


def _alias_map() -> dict[str, str]:
    """Official names plus accepted spellings, keyed by a fuzzy key."""
    keys: dict[str, str] = {}
    for _code, official in _load_rows():
        keys[_fuzzy_key(official)] = official
    for alias, official in ALIASES.items():
        keys.setdefault(_fuzzy_key(alias), official)
    return keys


def _fuzzy_key(text: str) -> str:
    """Lowercase and strip apostrophes, separators and the word 'county'."""
    for character in ("'", "’"):
        text = text.replace(character, "")
    for character in ("-", "/", ",", "."):
        text = text.replace(character, " ")
    words = [word for word in text.lower().split() if word != _COUNTY_WORD]
    return " ".join(words)


ALIASES: dict[str, str] = {
    # Spellings seen in real datasets that differ beyond punctuation from
    # the official name. Punctuation variants need no entry: _fuzzy_key
    # already folds hyphens, slashes and apostrophes into the official key.
    "Muranga": "Murang'a",
    "Homabay": "Homa Bay",
    "Nairobi City": "Nairobi",
    "WestPokot": "West Pokot",
    "ElgeyoMarakwet": "Elgeyo Marakwet",
    "TaitaTaveta": "Taita Taveta",
    "TharakaNithi": "Tharaka Nithi",
    "Uasingishu": "Uasin Gishu",
}


def _official_names() -> list[str]:
    return [name for _, name in _load_rows()]


def _exact_lookup(key: str) -> Result | None:
    official = _alias_map().get(key)
    if official is None:
        return None
    return Result(value=official, status="valid")


def _fuzzy_lookup(key: str) -> Result:
    close = difflib.get_close_matches(key, list(_alias_map()), n=3, cutoff=_FUZZY_CUTOFF)
    if not close:
        return Result(value=None, status="invalid", reason="not a recognized county name")
    # Several alias keys can map to the same official name; that is one
    # candidate, not an ambiguity. Only distinct counties are ambiguous.
    candidates: list[str] = []
    for candidate_key in close:
        official = _alias_map()[candidate_key]
        if official not in candidates:
            candidates.append(official)
    if len(candidates) > 1:
        return Result(
            value=None,
            status="ambiguous",
            reason="could be any of: " + ", ".join(candidates),
        )
    return Result(value=candidates[0], status="fixed", reason="matched alias, fuzzy")


def normalize(raw: str) -> Result:
    """Normalize one county name to the official name.

    Args:
        raw: The county name as found in the data, in any spelling.

    Returns:
        A Result whose value is the official county name when the status
        is "valid" or "fixed", and None otherwise. Use ``code_for`` to
        get the three-digit code.
    """
    if raw is None:
        return Result(value=None, status="invalid", reason="no county name found")
    text = str(raw).strip()
    if not text:
        return Result(value=None, status="invalid", reason="no county name found")
    key = _fuzzy_key(text)
    if not key:
        return Result(value=None, status="invalid", reason="no county name found")
    exact = _exact_lookup(key)
    if exact is not None:
        if text in _official_names():
            return exact
        return Result(value=exact.value, status="fixed", reason="matched alias, exact")
    return _fuzzy_lookup(key)


def code_for(name: str) -> str | None:
    """Return the three-digit county code for an official name, or None."""
    for code, official in _load_rows():
        if official == name:
            return code
    return None


def all_counties() -> dict[str, str]:
    """Return the full mapping of code to official name."""
    return dict(_load_rows())


__all__ = ["all_counties", "code_for", "normalize"]
