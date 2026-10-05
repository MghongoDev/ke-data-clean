"""Phase 4 checkpoint: counts add up, re-runs are idempotent, 100k rows stay fast.

Run it from the repository root with the project's virtual environment
active::

    python scripts/checkpoint.py            # 10,000 rows: correctness
    python scripts/checkpoint.py --rows 100000   # plus the timing run

The script generates a synthetic messy CSV with a fixed seed, runs
``ke-clean`` through its real entry point, and checks three things from
the implementation guide:

1. Every row lands in exactly one status per column; the report holds
   exactly the non-valid cells.
2. Running the cleaned output through again changes nothing
   (byte-identical outputs).
3. On 100,000 rows the run finishes in well under a minute.
"""

from __future__ import annotations

import argparse
import random
import tempfile
import time
from pathlib import Path

import pandas as pd

from ke_data_clean.cli import main

PHONES_MESSY = [
    "0712 345 678", "+254-720-111-222", "733987654", "0110 987 654",
    "0111 222 333", "254745999888", "+254799000111", "0759123456",
    "00254781234567", "(0716) 555-123",
]
PHONES_BAD = ["020 2318463", "07123456789", "0712 34", "O712345678", "12345", "041 2234567"]
PINS = ["A012345678B", "a012345678b", "P055555555x", "P987654321C", " A055555555Z "]
PINS_BAD = ["A01234567B", "A012345678BC", "1012345678B", "A012345678", "X012345678B"]
COUNTIES = ["Nairobi", "muranga", "Homabay", "Nairobi City", "Kilifi", "Uasin Gishu",
            "Mombasa", "kisumu", "west pokot", "Elgeyo Marakwet", "Kajiado", "Baringo"]
COUNTIES_BAD = ["kiifi", "Atlantis", "nairobii", "Taita tavetaa"]
AMOUNTS = ["Ksh 1,200/=", "450.00", "KES 89,999.99", "kshs.450.00", "1200", "1 200",
           "KES450", "0.50", "12,345.67"]
AMOUNTS_BAD = ["1.2k", "12.34.56", "-1200", "(1200)", "1,20,0", "1200 450", "KES", ""]


def _pick(pool: list[str], rng: random.Random) -> str:
    return rng.choice(pool)


def build_rows(count: int, seed: int) -> list[dict[str, str]]:
    """Synthetic messy rows: mostly cleanable, with a known share of problems."""
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    for _ in range(count):
        rows.append(
            {
                "phone_no": _pick(PHONES_MESSY + PHONES_BAD, rng),
                "kra_pin": _pick(PINS + PINS_BAD, rng),
                "county": _pick(COUNTIES + COUNTIES_BAD, rng),
                "total": _pick(AMOUNTS + AMOUNTS_BAD, rng),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    import csv

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["phone_no", "kra_pin", "county", "total"])
        writer.writeheader()
        writer.writerows(rows)


def clean(source: Path, out: Path, report: Path, strict: bool = False) -> int:
    argv = [
        str(source),
        "--phone", "phone_no",
        "--pin", "kra_pin",
        "--county", "county",
        "--amount", "total",
        "--out", str(out),
        "--report", str(report),
    ]
    if strict:
        argv.append("--strict")
    return main(argv)


def check_counts(out: Path, report: Path, row_count: int) -> None:
    """Every cell lands in exactly one status; the report holds the rest."""
    cleaned = pd.read_csv(out, dtype=str, keep_default_na=False, na_values=[""])
    statuses = ("valid", "fixed", "invalid", "ambiguous")
    non_valid_total = 0
    for kind in ("phone_no", "kra_pin", "county", "total"):
        column = cleaned[f"{kind}_status"]
        tally = sum(int((column == status).sum()) for status in statuses)
        if tally != row_count:
            raise SystemExit(f"counts do not add up for {kind}: {tally} != {row_count}")
        non_valid_total += int((column != "valid").sum())
    report_rows = pd.read_csv(report, dtype=str, keep_default_na=False, na_values=[""])
    if len(report_rows) != non_valid_total:
        raise SystemExit(
            f"report has {len(report_rows)} rows but data has {non_valid_total} non-valid cells"
        )
    print(f"counts add up: {row_count} rows, report holds {non_valid_total} non-valid cells")


def check_idempotent(first: Path, second: Path, report_one: Path, report_two: Path) -> None:
    for left, right in ((first, second), (report_one, report_two)):
        if left.read_bytes() != right.read_bytes():
            raise SystemExit(f"second run changed {left.name}")
    print("idempotent: second run is byte-identical")


def run_checkpoint(row_count: int, with_timing: bool) -> None:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        source = base / "messy.csv"
        write_csv(source, build_rows(row_count, seed=42))

        started = time.perf_counter()
        code = clean(source, base / "clean.csv", base / "changes.csv")
        elapsed = time.perf_counter() - started
        if code != 0:
            raise SystemExit(f"first run exited {code}")
        print(f"{row_count} rows cleaned in {elapsed:.1f}s")

        check_counts(base / "clean.csv", base / "changes.csv", row_count)

        code = clean(base / "clean.csv", base / "second.csv", base / "second_report.csv")
        if code != 0:
            raise SystemExit(f"second run exited {code}")
        check_idempotent(
            base / "clean.csv", base / "second.csv",
            base / "changes.csv", base / "second_report.csv",
        )

        if with_timing:
            big = base / "big.csv"
            write_csv(big, build_rows(100_000, seed=7))
            started = time.perf_counter()
            code = clean(big, base / "big_clean.csv", base / "big_report.csv")
            elapsed = time.perf_counter() - started
            if code != 0:
                raise SystemExit(f"100k run exited {code}")
            print(f"100,000 rows cleaned in {elapsed:.1f}s")
            if elapsed > 60:
                raise SystemExit("100k run took over a minute; cache or vectorize more")
            print("timing ok: under a minute")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=10_000, help="rows for the correctness run")
    parser.add_argument("--timing", action="store_true", help="also run the 100k timing checkpoint")
    arguments = parser.parse_args()
    run_checkpoint(arguments.rows, arguments.timing or arguments.rows >= 100_000)
