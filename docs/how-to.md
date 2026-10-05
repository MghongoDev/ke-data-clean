# How-to guides

Task-by-task recipes. Each one assumes the package is installed; see the [tutorial](tutorial.md) for setup.

## Clean one column of a pandas DataFrame

```python
import pandas as pd
from ke_data_clean.pandas_ext import clean_column

frame = pd.read_csv("customers.csv", dtype=str, keep_default_na=False, na_values=[""])
result = clean_column(frame["phone_no"], "phone")
frame["phone_no_clean"] = result["value"]
frame["phone_no_status"] = result["status"]
```

`clean_column` returns a DataFrame with `value`, `status` and `reason` columns and the same index as the input. It returns an object-dtype frame on purpose: missing values stay `None` instead of turning into `NaN`. Missing input becomes an `invalid` result with the reason `no value found`. Repeated raw values are cleaned once and reused from a cache, so a column with many duplicates stays fast.

Pass options through to the validator: `clean_column(frame["total"], "amount", allow_shorthand=True)`.

## Fail a pipeline when bad values remain

```bash
ke-clean customers.csv --phone phone_no --amount total \
  --out cleaned.csv --report changes.csv --strict
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Finished. `invalid` values may exist; read the report. |
| 1 | `--strict` was set and at least one value stayed `invalid`. |
| 2 | Usage or file problem: unknown column, unreadable file, output path pointing at the input. |

Without `--strict` the same run exits 0. Use `--strict` in CI or scheduled jobs where a silent bad column would flow downstream.

## Accept 1.2k-style amounts

```bash
ke-clean customers.csv --amount total ... --allow-shorthand
```

```python
money.parse_kes("1.2k", allow_shorthand=True)
# Result(value='1200', status='fixed', reason='expanded shorthand')
```

The flag exists because `1.2k` is ambiguous in business data: it can mean 1,200 or be a typo for 1.20. Opt in only when you know who typed the column. Ragged thousands grouping such as `1,20,0` stays rejected either way.

## Accept other KRA PIN prefixes

KRA documents A for individuals and P for companies, which is the default:

```python
pin.validate("A012345678B")
# Result(value='A012345678B', status='valid')
```

To accept another documented series, name its leading letter:

```python
pin.validate(raw, allowed_prefixes=("A", "P", "H"))
```

The format check stays the same: one letter, nine digits, one letter.

## Mask phone numbers and national IDs before sharing

```python
from ke_data_clean import mask

mask.phone("0712 345 678")
# Result(value='+25471*****78', status='fixed', reason='reformatted to E.164')

mask.national_id("12345678")
# Result(value='123***678', status='fixed', reason='masked for sharing')
```

The phone mask keeps the first six and last two characters of the E.164 form, so duplicates stay detectable. The ID mask always writes three stars whatever the length, so the mask does not reveal how long the ID is. Fewer than seven digits is refused: a shorter number would stay readable through the mask.

## Get county codes and the full list

```python
from ke_data_clean import county

county.code_for("Nairobi")
# '047'

counties = county.all_counties()   # {'001': 'Mombasa', ..., '047': 'Nairobi'}
```

Codes follow the First Schedule of the Constitution of Kenya (2010). Add `county_clean_code = county.code_for(result.value)` to a pipeline when you want a stable join key next to the name.

## Parse M-Pesa statement Details

```python
from ke_data_clean import mpesa

mpesa.parse_details("Pay Bill to KPLC POSTPAID - 888880 for account 123456789")
# Parsed(kind='paybill', id='888880', name='KPLC POSTPAID', account='123456789')

mpesa.parse_details("Some new statement wording")
# None
```

`None` means the line matched no known pattern. Filter those rows out and inspect them; the parser will not invent a shape. `Parsed` carries `kind`, `id`, `name` and `account` (the last only for paybill payments).

## Deal with an ambiguous county

The reason names every candidate:

```python
county.normalize("kiifi")
# Result(value=None, status='ambiguous', reason='could be any of: Kilifi, Kisii')
```

Three ways to resolve it:

1. Fix the source data to the official spelling (`Kilifi`).
2. Pick per row with extra context (for example the town column) and pass the choice downstream.
3. Keep the rows in a review queue. Do not code a "pick the first candidate" shortcut; the ambiguity is real.

## Work with the Result contract directly

Every validator returns the same frozen dataclass, so one helper can handle all kinds:

```python
from ke_data_clean.kinds import clean_value

clean_value("0712 345 678", "phone")
# Result(value='+254712345678', status='fixed', reason='reformatted to E.164')

clean_value("x", "nope")   # raises ValueError, listing the known kinds
```

The known kinds are `phone`, `pin`, `county` and `amount`. Use `clean_value` when the kind arrives as data, for example from a CLI flag or a config file.
