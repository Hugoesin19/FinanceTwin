"""Revenue stream — MOTOR §4.1 / §7.1–7.2."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class RevenueStream:
    id: str
    name: str
    start_t: int
    base_monthly_revenue: Decimal
    gross_margin_pct: Decimal
    collection_days: int = 0
    end_t: int | None = None
    growth_annual: Decimal = Decimal("0")
    ramp: Sequence[Decimal] | None = None
    seasonality: Sequence[Decimal] | None = None
    business_unit_id: str | None = None
