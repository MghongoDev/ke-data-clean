"""The ke-clean command: a messy CSV in, a cleaned CSV and a report out.

Usage::

    ke-clean FILE.csv --phone phone_no --pin kra_pin --county county \\
        --amount total --out cleaned.csv --report changes.csv

Original columns are never touched: each cleaned column is written
beside them as ``<col>_clean`` and ``<col>_status``. Re-running the
command on its own output is safe and changes nothing: a derived
column is rewritten only when it already holds exactly the values
this run would write, so a column ke-clean did not produce is refused
rather than clobbered. The report lists every row that was fixed, was
invalid, or was ambiguous. With ``--strict`` the command exits
non-zero when any value stays invalid, so a pipeline can fail on it.

Exit codes: 0 when clean (or only warnings), 1 when ``--strict`` found
invalid values, 2 for usage and file errors.
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

from ke_data_clean import __version__
from ke_data_clean.kinds import KINDS
from ke_data_clean.pandas_ext import clean_column

_SUFFIX_CLEAN = "_clean"
_SUFFIX_STATUS = "_status"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ke-clean",
        description="Clean Kenyan columns in a CSV: phones, KRA PINs, counties, KES amounts.",
    )
    parser.add_argument("file", help="the CSV file to clean")
    parser.add_argument(
        "--phone",
        action="append",
        default=[],
        metavar="COL",
        help="column holding phone numbers; repeat for more columns",
    )
    parser.add_argument(
        "--pin",
        action="append",
        default=[],
        metavar="COL",
        help="column holding KRA PINs; repeat for more columns",
    )
    parser.add_argument(
        "--county",
        action="append",
        default=[],
        metavar="COL",
        help="column holding county names; repeat for more columns",
    )
    parser.add_argument(
        "--amount",
        action="append",
        default=[],
        metavar="COL",
        help="column holding KES amounts; repeat for more columns",
    )
    parser.add_argument("--out", required=True, help="path for the cleaned CSV")
    parser.add_argument("--report", required=True, help="path for the change report CSV")
    parser.add_argument(
        "--allow-shorthand",
        action="store_true",
        help="accept 1.2k-style amounts (ambiguous in business data)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any value remains invalid, so pipelines can fail on it",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _targets_from(args: argparse.Namespace) -> dict[str, list[str]]:
    """Map each kind to the columns the user named for it."""
    targets: dict[str, list[str]] = {}
    for kind in KINDS:
        columns = getattr(args, kind)
        if columns:
            targets[kind] = columns
    return targets


def _check_columns_exist(frame: pd.DataFrame, targets: dict[str, list[str]]) -> str | None:
    for columns in targets.values():
        for column in columns:
            if column not in frame.columns:
                return (
                    f"column '{column}' not found in the input file. "
                    f"Columns present: {', '.join(frame.columns)}"
                )
    return None


def _same_path(left: str, right: str) -> bool:
    """Whether two paths point at the same file, resolving links."""
    return os.path.realpath(left) == os.path.realpath(right)


def _check_output_paths(args: argparse.Namespace) -> str | None:
    for label, path in (("out", args.out), ("report", args.report)):
        if _same_path(path, args.file):
            return (
                f"--{label} {path} is the input file itself; "
                "writing it would destroy the original data"
            )
    return None


def _existing_column_matches(frame: pd.DataFrame, name: str, computed: pd.Series) -> bool:
    """Whether ``name`` already holds exactly what this run would write.

    Missing values compare equal to missing values, so a re-run of
    ke-clean's own output (where invalid cells were written empty)
    matches.
    """
    existing = frame[name].astype(object).where(frame[name].notna(), "")
    computed = computed.astype(object).where(pd.notna(computed), "")
    return bool(existing.equals(computed))


def _check_would_not_clobber(
    frame: pd.DataFrame,
    results: dict[str, pd.DataFrame],
) -> str | None:
    """Refuse to replace a derived column that ke-clean did not produce.

    Re-running on ke-clean's own output must stay idempotent, so a
    ``<col>_clean`` or ``<col>_status`` column whose values match the
    recomputed ones is regenerated silently. A column that differs
    holds foreign data, and overwriting it would destroy that data.
    """
    for column, result_frame in results.items():
        for suffix, computed in (
            (_SUFFIX_CLEAN, result_frame["value"]),
            (_SUFFIX_STATUS, result_frame["status"]),
        ):
            name = column + suffix
            if name in frame.columns and not _existing_column_matches(frame, name, computed):
                return (
                    f"input already has a '{name}' column with values "
                    "ke-clean did not produce; overwriting it would destroy "
                    "data. Rename or drop it and run again"
                )
    return None


def _clean_all(
    frame: pd.DataFrame,
    targets: dict[str, list[str]],
    allow_shorthand: bool,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Return the frame with _clean/_status columns and each column's results."""
    cleaned = frame.copy()
    results: dict[str, pd.DataFrame] = {}
    for kind, columns in targets.items():
        # Only the amount validator takes allow_shorthand; handing the
        # flag to the other kinds would be a TypeError, not an ignore.
        options: dict[str, object] = (
            {"allow_shorthand": allow_shorthand} if kind == "amount" else {}
        )
        for column in columns:
            result_frame = clean_column(cleaned[column], kind, **options)
            results[column] = result_frame
            cleaned[column + _SUFFIX_CLEAN] = result_frame["value"]
            cleaned[column + _SUFFIX_STATUS] = result_frame["status"]
    return cleaned, results


def _build_report(
    original: pd.DataFrame,
    results: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """One row per non-valid cell: row number, column, original, new, status, reason.

    The columns are gathered as plain lists instead of row iteration:
    ``iterrows`` builds a Series per row, which dominates the runtime on
    six-figure row counts.
    """
    row_numbers: list[int] = []
    columns: list[str] = []
    originals: list[object] = []
    new_values: list[object] = []
    statuses: list[str] = []
    reasons: list[str] = []
    for column, result_frame in results.items():
        changed = result_frame[result_frame["status"] != "valid"]
        row_numbers.extend(position + 1 for position in changed.index.tolist())
        columns.extend([column] * len(changed))
        originals.extend(original.loc[changed.index, column].tolist())
        new_values.extend(
            value if value is not None else "" for value in changed["value"].tolist()
        )
        statuses.extend(changed["status"].tolist())
        reasons.extend(changed["reason"].tolist())
    return pd.DataFrame(
        {
            "row": row_numbers,
            "column": columns,
            "original": originals,
            "new": new_values,
            "status": statuses,
            "reason": reasons,
        },
        dtype=object,
    )


def _summarize(results: dict[str, pd.DataFrame]) -> str:
    lines = []
    statuses = ("valid", "fixed", "invalid", "ambiguous")
    for column, result_frame in results.items():
        counts = result_frame["status"].value_counts()
        tally = ", ".join(f"{counts.get(status, 0)} {status}" for status in statuses)
        lines.append(f"{column}: {tally}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ke-clean console script."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        frame = pd.read_csv(args.file, dtype=str, keep_default_na=False, na_values=[""])
    except (OSError, UnicodeDecodeError, pd.errors.ParserError) as error:
        print(f"ke-clean: cannot read {args.file}: {error}", file=sys.stderr)
        return 2
    if not isinstance(frame.index, pd.RangeIndex):
        # read_csv silently turns the first field into the index when a row
        # has exactly one field more than the header. Refuse rather than
        # clean shifted columns.
        print(
            f"ke-clean: cannot read {args.file} as a table: a data row has "
            "more fields than the header; check quoting of values with commas",
            file=sys.stderr,
        )
        return 2
    targets = _targets_from(args)
    if not targets:
        print(
            "ke-clean: name at least one column to clean, "
            "for example --phone phone_no. Kinds: " + ", ".join(sorted(KINDS)),
            file=sys.stderr,
        )
        return 2
    checks = (_check_columns_exist(frame, targets), _check_output_paths(args))
    for problem in checks:
        if problem:
            print(f"ke-clean: {problem}", file=sys.stderr)
            return 2
    cleaned, results = _clean_all(frame, targets, args.allow_shorthand)
    clobber = _check_would_not_clobber(frame, results)
    if clobber:
        print(f"ke-clean: {clobber}", file=sys.stderr)
        return 2
    report = _build_report(frame, results)
    cleaned.to_csv(args.out, index=False)
    report.to_csv(args.report, index=False)
    print(_summarize(results))
    print(f"wrote {args.out} and {args.report} ({len(report)} report rows)")
    if args.strict and (report["status"] == "invalid").any():
        print("ke-clean: --strict: invalid values remain", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
