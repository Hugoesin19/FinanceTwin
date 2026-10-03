"""Time helpers — MODELO §11.1."""

from __future__ import annotations

import re

_YM = re.compile(r"^(\d{4})-(\d{2})$")


def parse_year_month(value: str) -> tuple[int, int]:
    m = _YM.match(value)
    if not m:
        raise ValueError(f"invalid YearMonth: {value!r}")
    year, month = int(m.group(1)), int(m.group(2))
    if month < 1 or month > 12:
        raise ValueError(f"invalid YearMonth month: {value!r}")
    return year, month


def add_months(year_month: str, delta: int) -> str:
    """Suma (o resta) meses a un YearMonth YYYY-MM."""
    year, month = parse_year_month(year_month)
    idx = year * 12 + (month - 1) + delta
    if idx < 0:
        raise ValueError(f"year_month underflow: {year_month} + {delta}")
    new_year, new_month0 = divmod(idx, 12)
    return f"{new_year:04d}-{new_month0 + 1:02d}"


def months_between(anchor: str, target: str) -> int:
    """
    months_between(anchor, target) =
      (year(target) - year(anchor)) * 12 + (month(target) - month(anchor))
    """
    ay, am = parse_year_month(anchor)
    ty, tm = parse_year_month(target)
    return (ty - ay) * 12 + (tm - am)
