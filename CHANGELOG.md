# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-11-19

### Fixed

- Documentation links in the PyPI description now point to the repository files instead of paths under pypi.org, which returned 404.

### Added

- A Documentation project URL in the package metadata, so the project links on PyPI lead to the guides.

## [0.1.0] - 2026-10-05

First release.

### Added

- The `Result` contract (`value`, `status`, `reason`) shared by every validator. Nothing is fixed silently: `fixed` changes are mechanical and reported, `invalid` and `ambiguous` refuse with a reason.
- `phone.normalize`: Kenyan mobile numbers to E.164. The 7-series is accepted as a block; the fragmented 1-series is accepted only on its assigned prefixes; landlines are rejected with a reason.
- `pin.validate`: KRA PIN format check (letter, 9 digits, letter), default prefixes A and P, configurable.
- `money.parse_kes`: KES amounts from decorated text to canonical decimal strings. Ragged thousands grouping and negatives are rejected; `1.2k` shorthand is opt-in.
- `county.normalize`, `county.code_for`, `county.all_counties`: all 47 counties with official names and constitutional codes (001-047), alias and fuzzy matching, and `ambiguous` instead of a guess when two counties fit equally well.
- `mpesa.parse_details`: M-Pesa statement Details lines into `Parsed(kind, id, name, account)`; unknown shapes return `None`.
- `mask.phone` and `mask.national_id`: fixed-width masks for sharing extracts under the Data Protection Act, 2019.
- `kinds.clean_value`: one dispatch table shared by the pandas helper and the CLI.
- `pandas_ext.clean_column` (pandas extra): one column to `value`/`status`/`reason` with cached repeats.
- The `ke-clean` command (cli extra): cleans named columns beside the originals, writes an auditable change report, `--strict` for pipelines, idempotent re-runs, refuses to clobber data it did not produce.

### Sources for the rules (checked at release)

- Phone numbering plan: Communications Authority of Kenya assignments via libphonenumber metadata for +254, retrieved October 2026.
- KRA PIN format: KRA publications on kra.go.ke, September 2024 (A0… individuals, P0… companies).
- Counties: First Schedule of the Constitution of Kenya (2010).
