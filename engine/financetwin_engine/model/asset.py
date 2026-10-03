"""Asset — MOTOR §4.1 / §7.4."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

DepreciationMethod = Literal["straight_line", "declining_simple"]


@dataclass(frozen=True)
class Asset:
    id: str
    name: str
    acquisition_cost: Decimal
    acquisition_t: int
    useful_life_months: int
    residual_value: Decimal = Decimal("0")
    depreciation_method: DepreciationMethod = "straight_line"
    acquisition_funding: str = "cash"
    investment_id: str | None = None
