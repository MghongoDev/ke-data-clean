# Code complexity report

Per-function cyclomatic complexity for `src/ke_data_clean`, measured with
`scripts/complexity_report.py` (classic McCabe rules: one point per branch,
loop, except handler, ternary, assert, match case and comprehension clause,
plus one per boolean operator beyond the first, plus one for the function
itself). Nested functions are reported separately.

The enforced gate is ruff's C901 at complexity 10 (`pyproject.toml`). This
report counts more strictly than ruff, so a clean report here implies a
clean `ruff check --select C901`. Regenerate after changes:

```bash
python scripts/complexity_report.py
```

Measured at release 0.1.0: 43 functions, none over the gate.

| Complexity | Function | Gate |
|-----------:|----------|:----:|
| 9 | `cli.main` | ok |
| 8 | `phone.normalize` | ok |
| 8 | `money.parse_kes` | ok |
| 7 | `phone._judge_national` | ok |
| 7 | `money._split_groups` | ok |
| 6 | `money._canonicalize_number` | ok |
| 6 | `pin._shape_error` | ok |
| 6 | `mask.national_id` | ok |
| 6 | `county.normalize` | ok |
| 5 | `cli._build_report` | ok |
| 5 | `cli._check_would_not_clobber` | ok |
| 5 | `county._fuzzy_key` | ok |
| 5 | `county._fuzzy_lookup` | ok |
| 5 | `money._last_group_ok` | ok |
| 5 | `mpesa.parse_details` | ok |
| 5 | `pin.validate` | ok |
| 4 | `cli._check_columns_exist` | ok |
| 4 | `cli._clean_all` | ok |
| 4 | `phone._to_national` | ok |
| 4 | `pandas_ext.clean_column` | ok |
| 3 | `county._alias_map` | ok |
| 3 | `pandas_ext._cache_key` | ok |
| 3 | `pin._canonicalize` | ok |
| 3 | `cli._check_output_paths` | ok |
| 3 | `county._code_of` | ok |
| 3 | `money._middle_groups_ok` | ok |
| 3 | `money._reject_or_expand_shorthand` | ok |
| 3 | `cli._summarize` | ok |
| 3 | `cli._targets_from` | ok |
| 3 | `county.code_for` | ok |
| 2 | `county._exact_lookup` | ok |
| 2 | `money._first_group_ok` | ok |
| 2 | `county._load_rows` | ok |
| 2 | `county._official_names` | ok |
| 2 | `kinds.clean_value` | ok |
| 2 | `mask.phone` | ok |
| 1 | `cli._existing_column_matches` | ok |
| 1 | `pandas_ext._missing_result` | ok |
| 1 | `money._remove_decorations` | ok |
| 1 | `cli._same_path` | ok |
| 1 | `phone._strip` | ok |
| 1 | `county.all_counties` | ok |
| 1 | `cli.build_parser` | ok |
