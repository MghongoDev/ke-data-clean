# ke-data-clean

Clean the dirty fields Kenyan datasets keep arriving with. Free, open source (MIT), zero dependencies.

- Phone numbers in a dozen formats → E.164 (`+2547XXXXXXXX`, `+2541XXXXXXXX`)
- KRA PINs → format-checked (shape only; it cannot prove a PIN exists)
- County names spelled five ways → the official name and code, all 47 counties
- KES amounts stored as text → `Decimal`
- M-Pesa "Details" strings → sender kind, id, name and account

**Nothing is fixed silently.** Every validator returns a `Result` with a value, a status and a reason. The CLI writes a change report listing every change it made, so you can audit what happened to your data.

## Before and after

Ten messy rows in, cleaned values out. This table is the spec the package is tested against.

| # | Column | Messy input | Cleaned output | Status | Reason |
|---|--------|-------------|----------------|--------|--------|
| 1 | phone | `0712 345 678` | `+254712345678` | fixed | reformatted to E.164 |
| 2 | phone | `+254-712-345-678` | `+254712345678` | fixed | reformatted to E.164 |
| 3 | phone | `712345678` | `+254712345678` | fixed | reformatted to E.164 |
| 4 | phone | `0110 987 654` | `+254110987654` | fixed | reformatted to E.164 |
| 5 | phone | `07123456789` | *(empty)* | invalid | too long for a Kenyan mobile |
| 6 | county | `Murang'a` | `Murang'a` (021) | valid | |
| 7 | county | `muranga` | `Murang'a` (021) | fixed | matched alias, fuzzy |
| 8 | county | `Nairobi City` | `Nairobi` (047) | fixed | matched alias, exact |
| 9 | amount | `Ksh 1,200/=` | `1200.00` | fixed | parsed KES amount |
| 10 | pin | `A0039284B ` | `A0039284B` | fixed | trimmed spaces |

## Install

```bash
pip install ke-data-clean
```

Optional extras:

```bash
pip install "ke-data-clean[pandas]"   # clean_column helper
pip install "ke-data-clean[cli]"      # ke-clean command
```

## Quick start

```python
from ke_data_clean import phone

result = phone.normalize("0712 345 678")
print(result)
# Result(value='+254712345678', status='fixed', reason='reformatted to E.164')
```

### Clean a CSV from the command line

```bash
ke-clean customers.csv \
  --phone phone_no --pin kra_pin --county county --amount total \
  --out cleaned.csv --report changes.csv
```

The command writes `<col>_clean` and `<col>_status` columns beside the originals. It never overwrites your data. It prints a summary of counts by status per column. With `--strict`, it exits non-zero when any value stays `invalid`, so a pipeline can fail on it.

## Statuses

| Status | Meaning | Value |
|--------|---------|-------|
| `valid` | Already clean | unchanged |
| `fixed` | Cleaned, and the change is recorded | new value |
| `invalid` | Cannot be cleaned; the reason says why | `None` |
| `ambiguous` | Two or more equally close matches; the tool refuses to guess | `None` |

## Limitations

- KRA PIN validation checks format only. It cannot prove a PIN exists at KRA.
- County data covers the 47 counties of Kenya (constitution of 2010). Wards and constituencies are not covered yet.
- KES shorthand like `1.2k` is not parsed unless you opt in. In business data it is ambiguous.
- Landline numbers are rejected with a reason. Mobile-only for now.
- Formats follow the Kenyan numbering plan and county lists as understood at release time. Verify against the Communications Authority and KNBS before you rely on this in production. Sources and dates are in the module docstrings.

## Documentation

- [Getting started](docs/tutorial.md) — a worked tutorial from raw CSV to cleaned output
- [How-to guides](docs/how-to.md) — specific tasks: pandas, CLI, strict mode, masking
- [Reference](docs/reference.md) — every public function and its signatures
- [Explanation](docs/explanation.md) — why the Result contract exists, and the rules behind each validator

## Contributing

Issues and pull requests are welcome. Run `ruff check .` and `pytest` before you submit. Rule changes (phone prefixes, county data) must cite a primary source in the changelog.

## License

MIT. See [LICENSE](LICENSE).
