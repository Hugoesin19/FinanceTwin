"""P&L, cash flow, debt, investment metrics."""

from financetwin_engine.calc.assets import AssetDepreciationRow, build_asset_depreciation
from financetwin_engine.calc.capex import compute_capex_by_t
from financetwin_engine.calc.cash import (
    FinancingNeed,
    MonthlyCashFlow,
    build_cash_flow_series,
    compute_financing_need,
)
from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.calc.loans import LoanSchedule, LoanScheduleRow, build_loan_schedule
from financetwin_engine.calc.metrics import InvestmentMetrics, calculate_investment_metrics
from financetwin_engine.calc.pnl import MonthlyPnL, assemble_monthly_pnl, build_pnl_series

__all__ = [
    "D",
    "money",
    "InvestmentMetrics",
    "calculate_investment_metrics",
    "LoanSchedule",
    "LoanScheduleRow",
    "build_loan_schedule",
    "AssetDepreciationRow",
    "build_asset_depreciation",
    "MonthlyPnL",
    "assemble_monthly_pnl",
    "build_pnl_series",
    "MonthlyCashFlow",
    "FinancingNeed",
    "build_cash_flow_series",
    "compute_financing_need",
    "compute_capex_by_t",
]
