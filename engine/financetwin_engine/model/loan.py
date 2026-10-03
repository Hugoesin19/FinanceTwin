"""Loan entity for engine calculation input — MOTOR §4.1."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

AmortizationSystem = Literal["french", "linear", "bullet"]
GraceType = Literal["capital", "total"]


@dataclass(frozen=True)
class Loan:
    id: str
    name: str
    principal: Decimal
    annual_interest_rate: Decimal
    term_months: int
    amortization_system: AmortizationSystem
    disbursement_t: int = 0
    grace_months: int = 0
    grace_type: GraceType = "capital"
    origination_fee: Decimal = Decimal("0")
    rate_type: Literal["fixed"] = "fixed"
    # Adapter mapper (ADR 0001): deuda ya viva sin nueva disposición de caja
    skip_drawdown: bool = False
