"""Tests for county normalization against the 47-county dataset."""

from __future__ import annotations

import pytest

from ke_data_clean.county import all_counties, code_for, normalize

# The guide requires 20 messy variants that must resolve correctly.
MESSY_VARIANTS = [
    ("muranga", "Murang'a", "fixed"),
    ("Murang'a", "Murang'a", "valid"),
    ("MURANG'A COUNTY", "Murang'a", "fixed"),
    ("Nairobi City", "Nairobi", "fixed"),
    ("nairobi", "Nairobi", "fixed"),
    ("NAIROBI", "Nairobi", "fixed"),
    ("Homabay", "Homa Bay", "fixed"),
    ("homa bay county", "Homa Bay", "fixed"),
    ("Trans Nzoia", "Trans Nzoia", "valid"),
    ("trans-nzoia", "Trans Nzoia", "fixed"),
    ("Elgeyo Marakwet", "Elgeyo Marakwet", "valid"),
    ("elgeyo-marakwet", "Elgeyo Marakwet", "fixed"),
    ("Taita/Taveta", "Taita Taveta", "fixed"),
    ("taita taveta", "Taita Taveta", "fixed"),
    ("Tharaka-Nithi", "Tharaka Nithi", "fixed"),
    ("tharaka nithi county", "Tharaka Nithi", "fixed"),
    ("Uasin Gishu", "Uasin Gishu", "valid"),
    ("uasingishu", "Uasin Gishu", "fixed"),
    ("WestPokot", "West Pokot", "fixed"),
    ("mombasa county", "Mombasa", "fixed"),
]


def test_all_47_counties_load() -> None:
    counties = all_counties()
    assert len(counties) == 47
    assert counties["001"] == "Mombasa"
    assert counties["047"] == "Nairobi"


def test_every_official_name_resolves_exactly() -> None:
    for name in all_counties().values():
        result = normalize(name)
        assert result.status == "valid", f"{name}: {result}"
        assert result.value == name


@pytest.mark.parametrize(("raw", "expected", "expected_status"), MESSY_VARIANTS)
def test_messy_variants(raw: str, expected: str, expected_status: str) -> None:
    result = normalize(raw)
    assert result.value == expected
    assert result.status == expected_status


def test_two_way_fuzzy_match_returns_ambiguous_not_a_guess() -> None:
    # "kiifi" sits as close to Kilifi as to Kisii. The tool must refuse to
    # choose and must name both candidates.
    result = normalize("kiifi")
    assert result.status == "ambiguous"
    assert result.value is None
    assert "Kilifi" in result.reason
    assert "Kisii" in result.reason


def test_code_lookup() -> None:
    assert code_for("Mombasa") == "001"
    assert code_for("Murang'a") == "021"
    assert code_for("Nairobi") == "047"
    assert code_for("Homa Bay") == "043"
    assert code_for("Not A County") is None


def test_result_carries_code_in_documented_flow() -> None:
    result = normalize("muranga")
    assert result.value == "Murang'a"
    assert code_for(result.value) == "021"


def test_empty_and_none_are_invalid() -> None:
    assert normalize("").status == "invalid"
    assert normalize("   ").status == "invalid"
    assert normalize(None).status == "invalid"  # type: ignore[arg-type]


def test_unknown_name_is_invalid_with_reason() -> None:
    result = normalize("Atlantis")
    assert result.status == "invalid"
    assert result.reason
