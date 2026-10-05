"""pandas helper: clean one column into value, status and reason.

``clean_column`` applies a registered validator to every row and
returns a DataFrame with the same index. Repeated raw values are
cleaned once and re-used, which keeps a column of 100k rows with many
duplicates fast.

Requires the ``pandas`` extra: ``pip install "ke-data-clean[pandas]"``.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ke_data_clean.kinds import clean_value
from ke_data_clean.result import Result

_MISSING_REASON = "no value found"


def _missing_result() -> Result:
    return Result(value=None, status="invalid", reason=_MISSING_REASON)


def _cache_key(raw: Any, options: dict[str, object]) -> tuple[bool, str, tuple]:
    """A hashable key so repeated values (including missing) hit the cache."""
    if raw is None or pd.isna(raw):
        return (True, "", tuple(sorted(options.items())))
    return (False, str(raw), tuple(sorted(options.items())))


def clean_column(
    series: pd.Series,
    kind: str,
    **options: object,
) -> pd.DataFrame:
    """Clean one column with the validator registered for ``kind``.

    Args:
        series: The column to clean. Missing values (None, NaN, NA)
            become invalid results with the reason "no value found".
        kind: One of "phone", "pin", "county", "amount".
        **options: Forwarded to the validator.

    Returns:
        A DataFrame with the same index as ``series`` and three columns:
        ``value`` (object, None where invalid), ``status`` and ``reason``.
        The input series is never modified.

    Raises:
        ValueError: When the kind is not registered.
    """
    cache: dict[tuple, Result] = {}
    values: list[str | None] = []
    statuses: list[str] = []
    reasons: list[str] = []
    for raw in series:
        key = _cache_key(raw, options)
        result = cache.get(key)
        if result is None:
            result = _missing_result() if key[0] else clean_value(str(raw), kind, **options)
            cache[key] = result
        values.append(result.value)
        statuses.append(result.status)
        reasons.append(result.reason)
    return pd.DataFrame(
        {"value": values, "status": statuses, "reason": reasons},
        index=series.index,
        dtype=object,
    )


__all__ = ["clean_column"]
