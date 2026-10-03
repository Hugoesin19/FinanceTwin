"""Cost and payroll — MOTOR §4.1 / §7.3."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Sequence

CostNature = Literal["fixed", "variable_pct_revenue"]


@dataclass(frozen=True)
class CostItem:
    id: str
    name: str
    start_t: int
    nature: CostNature
    payment_days: int = 30
    end_t: int | None = None
    amount_monthly: Decimal | None = None
    pct_of_revenue: Decimal | None = None
    growth_annual: Decimal = Decimal("0")
    seasonality: Sequence[Decimal] | None = None
    business_unit_id: str | None = None


@dataclass(frozen=True)
class PayrollLine:
    id: str
    role_name: str
    headcount: int
    monthly_employer_cost: Decimal
    start_t: int
    end_t: int | None = None
    business_unit_id: str | None = None
    payment_days: int = 0
