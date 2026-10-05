# Explanation

Why ke-data-clean works the way it works.

## The contract exists because silent fixes destroy data

A phone column that arrives as `0712 345 678`, `+254-712-345-678` and `712345678` is the same number three times. A column with `07123456789` (ten digits) is a different problem: some digit is wrong, and no tool can know which. The failure mode this package guards against is the second case being quietly "fixed" into a plausible number that belongs to somebody else.

So every validator returns the same frozen dataclass:

```python
Result(value=..., status="valid" | "fixed" | "invalid" | "ambiguous", reason=...)
```

Four statuses, no exceptions:

- **valid** means the input already had the canonical shape. The tool touched nothing.
- **fixed** means the tool made a mechanical change it can defend: removing spaces, uppercasing, expanding a documented shorthand. Every fix lands in the change report with its reason.
- **invalid** means the tool refused. The reason states the specific failure (`expected 9 digits, got 10`), so a human can correct the source instead of guessing what the tool meant.
- **ambiguous** means two answers fit equally well. The tool names the candidates and stops. A wrong pick here is silent corruption; an empty cell with a reason is a work item.

`value` is a string or `None` so the contract stays identical across validators. Amounts are canonical decimal *strings* (`1200`, `1200.50`); wrap them with `Decimal(result.value)` for arithmetic. Floats were never considered: `0.1 + 0.2` has no place near money.

## Why some plausible-looking inputs are rejected on purpose

**Shorthand (`1.2k`) is opt-in.** In business data `1.2k` usually means 1,200, but it can be a typo for 1.20 — a thousandfold error. The caller who knows the column's provenance opts in with `allow_shorthand=True`; everyone else gets an `invalid` with that exact explanation.

**Ragged grouping (`1,20,0`) is always rejected.** Real thousands grouping has a first group of 1–3 digits and later groups of exactly 3. `1,20,0` could be 1,200 with mangled separators or three numbers. Collapsing it would be a guess wearing a parse's clothes.

**The 1-series needs a prefix list.** Kenyan mobiles live on the 7-series (700–799, assigned as a block) and the 1-series, which the Communications Authority assigned piecemeal from 2019. A rule like "starts with 7 or 1" would accept numbers on unassigned 1-prefixes. The package keeps the assigned prefixes explicitly (`_ONE_SERIES_PREFIXES`, from libphonenumber metadata for +254, retrieved October 2026) and rejects the rest. A randomized test cross-checks this list against the `phonenumbers` package. A first version of this rule over-accepted; the cross-check caught it, which is why the cross-check stays in the suite.

**Landlines are deferred, not approximated.** Area codes 2–6 identify landlines unambiguously, so they are rejected with a reason instead of being silently dropped or mis-shaped.

## Rules, and where they come from

Rule drift is a real risk: number plans change, and so does the data behind the rest of the rules. Every module docstring names its source and date, and the changelog records rule changes.

| Rule | Source | Checked |
|------|--------|---------|
| 9-digit NSN, 7-series block, 1-series prefixes | CA numbering plan via libphonenumber +254 metadata | October 2026 |
| PIN shape: letter + 9 digits + letter; A0… individuals, P0… companies | KRA blog on kra.go.ke | September 2024 |
| 47 counties, codes 001–047 | First Schedule, Constitution of Kenya (2010) | stable since 2010 |

Format checks can never prove existence: a format-valid PIN may not be registered, a valid E.164 number may be disconnected. That is why the README says format only.

## Why argparse, not typer

The CLI could have been thirty lines shorter with typer. It would also have pulled in `click`, breaking the zero-dependency promise for the `cli` extra — the people installing this are often in locked-down data environments where one extra transitive dependency is the difference between installing and not. argparse ships with Python, handles the flag surface (repeated flags, `--version`, help text) without ceremony, and its worst rough edges (manual exit codes) are exactly the behaviour this tool needs to control anyway. The command is small; the dependency list stays empty.

## Idempotency, and what the tool will not overwrite

`ke-clean` writes `<col>_clean` and `<col>_status` beside the originals and never writes to an original column. That alone would allow one nasty case: re-running on the command's own output would hit the derived columns, and a naive guard would refuse, so pipelines could not safely run twice. A naive non-guard would clobber a column somebody else named `phone_no_clean`.

The implemented rule splits the cases by content: a derived column is regenerated only when it already holds exactly the values this run computes. Re-running on ke-clean's own output is therefore a byte-for-byte fixpoint, while a foreign `phone_no_clean` column is refused with `exit 2` rather than destroyed. Similarly, `--out` or `--report` pointing at the input file is refused: writing cleaned data over the source is the one mistake there is no report to recover from.

## Why the masks have fixed widths

`mask.phone` writes exactly 5 stars and `mask.national_id` exactly 3, always. A mask that wrote one star per hidden digit would publish the length of every ID in the file — length itself leaks (older ID series differ from newer ones). Fewer than 7 digits is refused because keeping the first 3 and last 3 of a 6-digit number leaves nothing hidden.

## What this package is not

- Not a lookup service: nothing here queries KRA, the CA or an HLR.
- Not a landline formatter (deferred, with a reason when met).
- Not a ward/constituency gazetteer: counties only.
- Not a replacement for reviewing the change report. The report is the product; the cleaned CSV is its by-product.
