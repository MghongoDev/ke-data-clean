# Tutorial: clean a messy CSV from start to finish

This tutorial takes one small file of Kenyan customer data from raw to cleaned. You will run the `ke-clean` command, read its change report, then repeat the work in Python. It takes about ten minutes.

## What you need

Python 3.10 or newer. No other dependencies; pandas is optional and only used in the last step.

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install "ke-data-clean[cli]"
```

Check that the command exists:

```bash
ke-clean --version
```

## 2. Look at the data

Save this as `customers.csv`:

```csv
phone_no,kra_pin,county,total
0712 345 678,A012345678B,Nairobi,"Ksh 1,200/="
+254-720-111-222,P0555555555X,muranga,450.00
0733 987 654,a012345678b,Nairobi City,"KES 89,999.99"
020 2318463,A01234567B,Homabay,1.2k
+254110987654,A012345678B,kiifi,12.34.56
07123456789,A012345678B,Uasin Gishu,450
```

Six rows, four columns, and every column carries a different disease: phones in three formats, a landline, a PIN with twelve characters, a county spelled three ways, a KES amount with decorations, and `1.2k`, which could mean 1,200 or 1.20.

## 3. Run ke-clean

```bash
ke-clean customers.csv \
  --phone phone_no --pin kra_pin --county county --amount total \
  --out cleaned.csv --report changes.csv
```

The command prints one summary line per column:

```text
phone_no: 1 valid, 3 fixed, 2 invalid, 0 ambiguous
kra_pin: 3 valid, 1 fixed, 2 invalid, 0 ambiguous
county: 2 valid, 3 fixed, 0 invalid, 1 ambiguous
total: 2 valid, 2 fixed, 2 invalid, 0 ambiguous
wrote cleaned.csv and changes.csv (16 report rows)
```

Nothing was fixed silently. `cleaned.csv` holds your original columns untouched, with `phone_no_clean`, `phone_no_status` and the same pair for every other column beside them. Row 1 now looks like this:

| phone_no | county | total | phone_no_clean | phone_no_status | county_clean | total_clean | total_status |
|----------|--------|-------|----------------|-----------------|--------------|-------------|--------------|
| 0712 345 678 | Nairobi | `Ksh 1,200/=` | +254712345678 | fixed | Nairobi | 1200 | fixed |

## 4. Read the change report

`changes.csv` lists every cell the command did not leave alone:

```text
row,column,original,new,status,reason
1,phone_no,0712 345 678,+254712345678,fixed,reformatted to E.164
4,phone_no,020 2318463,,invalid,not a mobile number (landline support deferred)
6,phone_no,07123456789,,invalid,"expected 9 digits, got 10"
2,kra_pin,P0555555555X,,invalid,"expected 11 characters, got 12"
2,county,muranga,Murang'a,fixed,"matched alias, exact"
5,county,kiifi,,ambiguous,"could be any of: Kilifi, Kisii"
4,total,1.2k,,invalid,shorthand like 1.2k needs allow_shorthand=True because it is ambiguous in business data
```

Read the statuses like this:

- `fixed` — the tool changed the value, and the report says what it did.
- `invalid` — the tool refused. The reason says why. The `_clean` column holds an empty cell.
- `ambiguous` — two counties matched equally well, so the tool refused to guess.

Your job is to decide what happens to `invalid` and `ambiguous` rows: correct the source, ask the data owner, or drop the rows. The tool will not decide for you, because a wrong guess damages the data more than a missing value does.

## 5. Repeat the run

Run the same command on the cleaned file:

```bash
ke-clean cleaned.csv \
  --phone phone_no --pin kra_pin --county county --amount total \
  --out second.csv --report second_report.csv
```

`second.csv` is byte-for-byte the same as `cleaned.csv`. Running `ke-clean` on its own output changes nothing. This makes the command safe inside a pipeline that runs more than once.

## 6. Do the same in Python

The command is a wrapper around four validators. Each returns a `Result`:

```python
from ke_data_clean import county, money, phone, pin

phone.normalize("0712 345 678")
# Result(value='+254712345678', status='fixed', reason='reformatted to E.164')

pin.validate("a012345678b")
# Result(value='A012345678B', status='fixed', reason='uppercased')

county.normalize("kiifi")
# Result(value=None, status='ambiguous', reason='could be any of: Kilifi, Kisii')

money.parse_kes("Ksh 1,200/=")
# Result(value='1200', status='fixed', reason='parsed KES amount')
```

A `Result` has three fields: `value` (the cleaned string, or `None`), `status` (`valid`, `fixed`, `invalid` or `ambiguous`), and `reason` (empty only when the input was already clean). Amounts come back as canonical decimal strings; wrap them with `Decimal(result.value)` when you need to add them up.

## Next steps

- [How-to guides](how-to.md) for pandas columns, strict mode, masking and more
- [Reference](reference.md) for every function and flag
- [Explanation](explanation.md) for why the tool refuses instead of guessing
