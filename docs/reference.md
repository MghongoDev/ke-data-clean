# Reference

Every public function, its signature and its rules. The [tutorial](tutorial.md) shows these in action; the [explanation](explanation.md) says why the rules are what they are.

## The Result contract

```python
from ke_data_clean import Result, Status
```

```python
@dataclass(frozen=True)
class Result:
    value: str | None
    status: Status        # "valid" | "fixed" | "invalid" | "ambiguous"
    reason: str = ""
```

| Status | Meaning | `value` |
|--------|---------|---------|
| `valid` | Already clean | the input, unchanged |
| `fixed` | Cleaned; the report records what changed | the cleaned string |
| `invalid` | Refused; the reason says why | `None` |
| `ambiguous` | Several equally close answers; the tool refuses to guess | `None` |

`reason` is empty only for `valid`. Amount values are canonical decimal strings; call `Decimal(result.value)` to do arithmetic.

## phone.normalize

```python
phone.normalize(raw: str, default_region: str = "KE") -> Result
```

Normalizes a Kenyan mobile number to E.164 (`+254` plus 9 digits). Accepts `07xx`, `01xx`, bare 9-digit numbers, `254…`, `+254…` and `00254…`, with spaces, hyphens, brackets and dots stripped.

- The 7-series (700–799) is mobile as a block.
- The 1-series is fragmented: only the prefixes listed in `_ONE_SERIES_PREFIXES` are accepted. An unlisted 1-prefix is rejected, not guessed.
- Landlines (area codes 2–6) are rejected with the reason `not a mobile number (landline support deferred)`.

Prefix data: Communications Authority of Kenya assignments as captured in Google's libphonenumber metadata for +254, retrieved October 2026. The test suite cross-checks against the `phonenumbers` package on random numbers.

## pin.validate

```python
pin.validate(raw: str, allowed_prefixes: tuple[str, ...] = ("A", "P")) -> Result
```

Format check for one KRA PIN: one leading letter from `allowed_prefixes`, nine digits, one trailing letter (11 characters). Spaces are removed and lowercase letters are uppercased, which reports as `fixed`. Format only: a passing result does not prove the PIN exists at KRA.

## money.parse_kes

```python
money.parse_kes(raw: str, allow_shorthand: bool = False) -> Result
```

Parses one KES amount into a canonical decimal string. Handles `KES 1,200.50`, `Ksh. 1,200`, `KSh1200/=`, `1,200/-`, `1 200` and plain numbers.

Rejected, never guessed:

- negatives and bracket-negatives (`-1200`, `(1200)`)
- ragged thousands grouping (`1,20,0`)
- two numbers in one cell (`1200 450`)
- `1.2k`-style shorthand unless `allow_shorthand=True`

## county.normalize / code_for / all_counties

```python
county.normalize(raw: str) -> Result
county.code_for(name: str) -> str | None
county.all_counties() -> dict[str, str]   # code -> official name
```

Normalizes a county name to the official spelling for all 47 counties. Lookup order: exact alias match, then fuzzy match (`difflib.get_close_matches`, cutoff 0.75). Apostrophes, hyphens, slashes and the word "county" are folded away before matching, so `muranga`, `Murang'a` and `muranga county` all reach Murang'a (021). Two distinct counties matching equally well gives `ambiguous` with every candidate in the reason.

Data: First Schedule of the Constitution of Kenya (2010), code 001 Mombasa through 047 Nairobi, shipped as `data/counties.csv`. Common dataset spellings live in `county.ALIASES`.

## mpesa.parse_details

```python
mpesa.parse_details(text: str) -> Parsed | None
```

Parses one M-Pesa "Details" string from statements and B2C exports.

```python
@dataclass(frozen=True)
class Parsed:
    kind: str          # "send", "receive", "paybill", "buy_goods", ...
    id: str | None     # phone, paybill, till or agent number
    name: str | None
    account: str | None
```

Returns `None` for text that matches no known pattern.

## mask.phone / mask.national_id

```python
mask.phone(raw: str) -> Result          # '+25471*****78'
mask.national_id(raw: str) -> Result    # '123***678'
```

`mask.phone` normalizes to E.164 first, then keeps the first 6 and last 2 characters and writes 5 stars in between. Invalid numbers return the phone validator's result unchanged, reason included. `mask.national_id` keeps the first 3 and last 3 digits and always writes exactly 3 stars, so the mask never reveals the ID's length; fewer than 7 digits is refused.

Both helpers exist because phone numbers and ID numbers are personal data under Kenya's Data Protection Act, 2019. Mask extracts before you share them.

## kinds.clean_value

```python
from ke_data_clean.kinds import KINDS, clean_value

clean_value(raw: str, kind: str, **options: object) -> Result
```

Dispatch table shared by the pandas helper and the CLI. `kind` is one of `"phone"`, `"pin"`, `"county"`, `"amount"`; an unknown kind raises `ValueError` listing the known ones.

## pandas_ext.clean_column

Requires the `pandas` extra.

```python
clean_column(series: pd.Series, kind: str, **options: object) -> pd.DataFrame
```

Cleans every cell of one column and returns a DataFrame with `value`, `status` and `reason` columns, the same index as the input, and `dtype=object` so missing values stay `None`. Missing input gives an `invalid` result with the reason `no value found`. Repeated values are cached.

## The ke-clean command

```text
ke-clean FILE.csv --phone COL [--phone COL ...]
                 [--pin COL ...] [--county COL ...] [--amount COL ...]
                 --out CLEANED.csv --report CHANGES.csv
                 [--allow-shorthand] [--strict] [--version]
```

Each named column gets `<col>_clean` and `<col>_status` columns written beside the untouched originals. The report has one row per non-`valid` cell with the columns `row` (1-based data row), `column`, `original`, `new` (empty for `invalid` and `ambiguous`), `status` and `reason`.

Behaviour worth knowing:

- Original columns are never written to. Re-running on the command's own output reproduces it byte for byte.
- A `<col>_clean` or `<col>_status` column that already holds different values is refused (exit 2): ke-clean will not destroy data it did not produce.
- `--out` or `--report` pointing at the input file is refused (exit 2).
- `--allow-shorthand` is forwarded only to amount columns.

Source files for every rule: `src/ke_data_clean/*.py` module docstrings carry the rule, the source and the date it was checked.
