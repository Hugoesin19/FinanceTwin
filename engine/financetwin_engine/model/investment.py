"""Investment project — MOTOR §4.1 / MODELO §6.7."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class CapexPoint:
    t: int
    amount: Decimal
    includes_vat: bool = False
    label: str | None = None


@dataclass(frozen=True)
class Investment:
    id: str
    name: str
    capex_schedule: Sequence[CapexPoint]
    analysis_start_t: int = 0
    analysis_horizon_months: int | None = None
    linked_revenue_stream_ids: Sequence[str] = field(default_factory=tuple)
    linked_cost_item_ids: Sequence[str] = field(default_factory=tuple)
    linked_payroll_ids: Sequence[str] = field(default_factory=tuple)
    linked_loan_ids: Sequence[str] = field(default_factory=tuple)
    linked_asset_ids: Sequence[str] = field(default_factory=tuple)
    own_funds_t: int | None = None
    own_funds_amount: Decimal | None = None
    discount_rate_annual: Decimal | None = None
