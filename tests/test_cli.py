"""End-to-end tests for the ke-clean command."""

from __future__ import annotations

import csv
import subprocess

import pandas as pd
import pytest

from ke_data_clean.cli import build_parser, main

MESSY_ROWS = [
    # phone_no, kra_pin, county, total
    ("0712 345 678", "A012345678B", "Nairobi", "Ksh 1,200/="),
    ("+254-712-345-678", "a012345678b", "muranga", "1,200/-"),
    ("712345678", "P012345678X", "Nairobi City", "KES 1,200.50"),
    ("0110 987 654", "A012345678B", "Homabay", "450.00"),
    ("0202318463", "A012345678B", "Kisumu", "kshs.450.00"),  # landline -> invalid
    ("07123456789", "A01234567B", "Atlantis", "1.2k"),  # three invalids
    ("0712345678", "A012345678B", "kiifi", "12.34.56"),  # ambiguous county
    ("+254712345678", "A012345678B", "Uasin Gishu", "450"),
    ("0712 34", "A012345678B", "Kilifi", "KSh1200/="),
    ("O712345678", "A012345678B", "Kilifi", "450"),  # letter O
]
BASE_ARGS = ["--phone", "phone_no", "--pin", "kra_pin", "--county", "county", "--amount", "total"]


def write_messy_csv(path) -> None:
    # csv.writer quotes "Ksh 1,200/=" properly; joining with "," would
    # corrupt the CSV and shift every column after the first comma.
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["phone_no", "kra_pin", "county", "total"])
        writer.writerows(MESSY_ROWS)


def read_csv(path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def run(source, out, report, *extra: str) -> int:
    return main([str(source), *BASE_ARGS, *extra, "--out", str(out), "--report", str(report)])


def test_help_shows_the_target_shape(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--help"])
    assert exit_info.value.code == 0
    text = capsys.readouterr().out
    fragments = (
        "--phone COL", "--pin COL", "--county COL",
        "--amount COL", "--out", "--report", "--strict",
    )
    for fragment in fragments:
        assert fragment in text


def test_happy_path_writes_cleaned_and_report(tmp_path) -> None:
    source = tmp_path / "messy.csv"
    write_messy_csv(source)
    code = run(source, tmp_path / "clean.csv", tmp_path / "changes.csv")
    assert code == 0
    cleaned = read_csv(tmp_path / "clean.csv")
    # Originals untouched, new columns beside them
    assert cleaned["phone_no"].tolist() == [row[0] for row in MESSY_ROWS]
    assert "phone_no_clean" in cleaned.columns
    assert "phone_no_status" in cleaned.columns
    assert cleaned.loc[0, "phone_no_clean"] == "+254712345678"
    assert cleaned.loc[0, "county_clean"] == "Nairobi"
    assert cleaned.loc[0, "total_clean"] == "1200"
    # Counts add up: every row lands in exactly one status
    report = read_csv(tmp_path / "changes.csv")
    phone_status = cleaned["phone_no_status"].value_counts()
    statuses = ("valid", "fixed", "invalid", "ambiguous")
    tally = sum(phone_status.get(status, 0) for status in statuses)
    assert tally == len(MESSY_ROWS)
    phone_report = report[report["column"] == "phone_no"]
    non_valid = int((cleaned["phone_no_status"] != "valid").sum())
    assert len(phone_report) == non_valid
    # Every non-valid row appears in the report with its reason
    invalid = report[(report["column"] == "phone_no") & (report["status"] == "invalid")]
    assert "landline" in invalid.iloc[0]["reason"]


def test_idempotent_second_run_changes_nothing(tmp_path) -> None:
    source = tmp_path / "messy.csv"
    write_messy_csv(source)
    run(source, tmp_path / "first.csv", tmp_path / "r1.csv")
    code = run(tmp_path / "first.csv", tmp_path / "second.csv", tmp_path / "r2.csv")
    assert code == 0
    # Running the cleaned file through again is a fixpoint: both outputs
    # are byte-identical to the first run's, because the derived columns
    # already hold exactly what the second run computes.
    first = (tmp_path / "first.csv").read_text(encoding="utf-8")
    second = (tmp_path / "second.csv").read_text(encoding="utf-8")
    assert second == first
    report_one = (tmp_path / "r1.csv").read_text(encoding="utf-8")
    report_two = (tmp_path / "r2.csv").read_text(encoding="utf-8")
    assert report_two == report_one
    report = read_csv(tmp_path / "r2.csv")
    ambiguous = report[report["status"] == "ambiguous"]
    assert ambiguous.iloc[0]["reason"].startswith("could be")


def test_strict_exits_nonzero_when_invalids_remain(tmp_path) -> None:
    source = tmp_path / "messy.csv"
    write_messy_csv(source)
    code = run(source, tmp_path / "c.csv", tmp_path / "r.csv", "--strict")
    assert code == 1


def test_not_strict_exits_zero_despite_invalids(tmp_path) -> None:
    source = tmp_path / "messy.csv"
    write_messy_csv(source)
    code = run(source, tmp_path / "c.csv", tmp_path / "r.csv")
    assert code == 0


def test_missing_column_exits_two_with_message(tmp_path, capsys) -> None:
    source = tmp_path / "messy.csv"
    write_messy_csv(source)
    code = main([str(source), "--phone", "nope", "--out", "c.csv", "--report", "r.csv"])
    assert code == 2
    assert "nope" in capsys.readouterr().err


def test_no_targets_exits_two(tmp_path) -> None:
    source = tmp_path / "messy.csv"
    write_messy_csv(source)
    assert main([str(source), "--out", "c.csv", "--report", "r.csv"]) == 2


def test_missing_file_exits_two(tmp_path, capsys) -> None:
    ghost = tmp_path / "ghost.csv"
    code = main([str(ghost), "--phone", "p", "--out", "c.csv", "--report", "r.csv"])
    assert code == 2
    assert "cannot read" in capsys.readouterr().err


def test_row_with_more_fields_than_header_exits_two(tmp_path, capsys) -> None:
    # A value with an unquoted comma makes pandas shift the first field
    # into the index; ke-clean must refuse, not clean shifted columns.
    source = tmp_path / "ragged.csv"
    source.write_text("phone_no,total\n0712345678,1,200\n", encoding="utf-8")
    code = main([str(source), "--phone", "phone_no", "--out", "c.csv", "--report", "r.csv"])
    assert code == 2
    assert "more fields" in capsys.readouterr().err


def test_foreign_derived_column_is_refused(tmp_path, capsys) -> None:
    source = tmp_path / "already.csv"
    source.write_text(
        "phone_no,phone_no_clean\n0712345678,somebody elses value\n",
        encoding="utf-8",
    )
    code = main([str(source), "--phone", "phone_no", "--out", "c.csv", "--report", "r.csv"])
    assert code == 2
    assert "would destroy data" in capsys.readouterr().err


def test_output_path_equal_to_input_exits_two(tmp_path, capsys) -> None:
    source = tmp_path / "messy.csv"
    write_messy_csv(source)
    code = main(
        [str(source), "--phone", "phone_no", "--out", str(source), "--report", "r.csv"]
    )
    assert code == 2
    assert "destroy the original data" in capsys.readouterr().err
    code = main(
        [str(source), "--phone", "phone_no", "--out", "c.csv", "--report", str(source)]
    )
    assert code == 2
    assert "destroy the original data" in capsys.readouterr().err


def test_allow_shorthand_flag_flows_through(tmp_path) -> None:
    source = tmp_path / "amounts.csv"
    source.write_text("total\n1.2k\n", encoding="utf-8")
    code = main(
        [
            str(source),
            "--amount",
            "total",
            "--allow-shorthand",
            "--out",
            str(tmp_path / "c.csv"),
            "--report",
            str(tmp_path / "r.csv"),
        ]
    )
    assert code == 0
    cleaned = read_csv(tmp_path / "c.csv")
    assert cleaned.loc[0, "total_clean"] == "1200"
    assert cleaned.loc[0, "total_status"] == "fixed"


def test_shorthand_amount_is_invalid_without_the_flag(tmp_path) -> None:
    source = tmp_path / "amounts.csv"
    source.write_text("total\n1.2k\n", encoding="utf-8")
    code = main(
        [
            str(source),
            "--amount",
            "total",
            "--out",
            str(tmp_path / "c.csv"),
            "--report",
            str(tmp_path / "r.csv"),
        ]
    )
    assert code == 0
    cleaned = read_csv(tmp_path / "c.csv")
    assert cleaned.loc[0, "total_status"] == "invalid"


def test_console_script_is_installed() -> None:
    result = subprocess.run(
        ["ke-clean", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("ke-clean")
