"""Invariants — MOTOR §13."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.loans import LoanSchedule
from financetwin_engine.model.asset import Asset
from financetwin_engine.model.calculation import CalculationResult

TOL = D("0.01")
TOL_BALANCE = D("0.05")
ZERO = D(0)


class InvariantError(AssertionError):
    pass


def check_invariants(
    result: CalculationResult,
    *,
    assets: Sequence[Asset] = (),
    loan_term_ends: dict[str, int] | None = None,
) -> None:
    """Raise InvariantError if any MOTOR §13 check fails."""
    h = result.horizon_months
    if not (len(result.pnl) == len(result.cash_flow) == len(result.balance) == h):
        raise InvariantError("length mismatch pnl/cash/balance vs H")

    for t in range(h):
        pnl = result.pnl[t]
        cf = result.cash_flow[t]
        bal = result.balance[t]

        if abs(cf.closing_cash - (cf.opening_cash + cf.net_cash_flow)) > TOL:
            raise InvariantError(f"cash identity fail t={t}")
        if t + 1 < h:
            if abs(result.cash_flow[t + 1].opening_cash - cf.closing_cash) > TOL:
                raise InvariantError(f"cash continuity fail t={t}")

        if abs(pnl.gross_profit - (pnl.revenue - pnl.cogs)) > TOL:
            raise InvariantError(f"gross_profit fail t={t}")
        if abs(
            pnl.ebitda - (pnl.gross_profit - pnl.payroll_expense - pnl.other_opex)
        ) > TOL:
            raise InvariantError(f"ebitda fail t={t}")
        if abs(pnl.ebit - (pnl.ebitda - pnl.depreciation)) > TOL:
            raise InvariantError(f"ebit fail t={t}")
        if abs(pnl.ebt - (pnl.ebit - pnl.interest_expense)) > TOL:
            raise InvariantError(f"ebt fail t={t}")
        if abs(pnl.net_income - (pnl.ebt - pnl.corp_tax_expense)) > TOL:
            raise InvariantError(f"net_income fail t={t}")

        if abs(bal.total_assets - bal.total_liabilities_equity) > TOL_BALANCE:
            raise InvariantError(f"balance equation fail t={t}")

    # Loan final principal
    for loan_id, sched in result.loan_schedules.items():
        end_t = None if loan_term_ends is None else loan_term_ends.get(loan_id)
        if end_t is not None and end_t < h:
            if abs(sched.rows[end_t].closing_principal) > TOL:
                raise InvariantError(f"loan {loan_id} not fully repaid at end")

    # Accumulated depreciation ≤ depreciable base
    from financetwin_engine.calc.assets import build_asset_depreciation

    for asset in assets:
        rows = build_asset_depreciation(asset, h)
        max_dep = asset.acquisition_cost - asset.residual_value
        if rows and rows[-1].cumulative_depreciation - max_dep > TOL:
            raise InvariantError(f"asset {asset.id} over-depreciated")
