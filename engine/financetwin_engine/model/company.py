"""Company / fiscal / policy fragments for CalculationInput — MOTOR §4."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

VatSettlement = Literal["monthly", "quarterly"]
CorpTaxPaymentMode = Literal["none", "annual_end", "quarterly_approx"]


@dataclass(frozen=True)
class FiscalConfig:
    vat_rate: Decimal = Decimal("0")
    vat_settlement: VatSettlement = "monthly"
    vat_payment_lag_months: int = 0
    corp_tax_rate: Decimal = Decimal("0")
    corp_tax_payment_mode: CorpTaxPaymentMode = "none"


@dataclass(frozen=True)
class CompanyPolicy:
    min_cash: Decimal = Decimal("0")
    max_debt_ebitda: Decimal | None = None
    min_dscr: Decimal | None = None
    max_payback_months: int | None = None
    min_irr: Decimal | None = None
    max_capex_pct_cash: Decimal | None = None


@dataclass(frozen=True)
class CompanyInput:
    currency: str = "EUR"
    opening_cash: Decimal = Decimal("0")
    default_purchase_payment_days: int = 30
    fiscal: FiscalConfig = field(default_factory=FiscalConfig)
    policies: CompanyPolicy = field(default_factory=CompanyPolicy)
