"""CalculationInput / CalculationResult — MOTOR §4–§5."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Sequence

from financetwin_engine.model.asset import Asset
from financetwin_engine.model.company import CompanyInput
from financetwin_engine.model.costs import CostItem, PayrollLine
from financetwin_engine.model.investment import Investment
from financetwin_engine.model.loan import Loan
from financetwin_engine.model.one_off import OneOffCashEvent
from financetwin_engine.model.revenue import RevenueStream

if TYPE_CHECKING:
    from financetwin_engine.calc.cash import FinancingNeed, MonthlyCashFlow
    from financetwin_engine.calc.loans import LoanSchedule
    from financetwin_engine.calc.metrics import InvestmentMetrics
    from financetwin_engine.calc.pnl import MonthlyPnL


@dataclass(frozen=True)
class CalculationInput:
    company: CompanyInput
    horizon_months: int
    discount_rate_annual: Decimal = Decimal("0")
    auto_finance_deficits: bool = False
    revenue_streams: Sequence[RevenueStream] = field(default_factory=tuple)
    cost_items: Sequence[CostItem] = field(default_factory=tuple)
    payroll: Sequence[PayrollLine] = field(default_factory=tuple)
    loans: Sequence[Loan] = field(default_factory=tuple)
    assets: Sequence[Asset] = field(default_factory=tuple)
    investments: Sequence[Investment] = field(default_factory=tuple)
    one_off_cash_events: Sequence[OneOffCashEvent] = field(default_factory=tuple)


@dataclass(frozen=True)
class MonthlyBalance:
    t: int
    non_current_assets_net: Decimal
    accounts_receivable: Decimal
    cash: Decimal
    total_assets: Decimal
    debt_long_term: Decimal
    debt_short_term: Decimal
    accounts_payable: Decimal
    vat_payable: Decimal
    corp_tax_payable: Decimal
    equity: Decimal
    total_liabilities_equity: Decimal


@dataclass(frozen=True)
class PolicyCheck:
    policy_id: str
    status: str  # pass | fail | skip
    message: str
    value: Decimal | None = None
    threshold: Decimal | None = None


@dataclass(frozen=True)
class CalculationResult:
    engine_version: str
    inputs_hash: str
    result_hash: str
    horizon_months: int
    pnl: tuple[MonthlyPnL, ...]
    cash_flow: tuple[MonthlyCashFlow, ...]
    balance: tuple[MonthlyBalance, ...]
    loan_schedules: dict[str, LoanSchedule]
    investment_metrics: InvestmentMetrics | None
    financing_need: FinancingNeed
    policy_checks: tuple[PolicyCheck, ...]
    warnings: tuple[str, ...]
    simplifications_applied: tuple[str, ...]
