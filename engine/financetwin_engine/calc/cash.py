"""Cash flow, AR/AP, financing need — MOTOR §8, §11."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.calc.loans import LoanSchedule
from financetwin_engine.calc.pnl import MonthlyPnL
from financetwin_engine.model.costs import CostItem, PayrollLine
from financetwin_engine.model.one_off import OneOffCashEvent
from financetwin_engine.model.revenue import RevenueStream

ZERO = D(0)
ONE = D(1)


@dataclass(frozen=True)
class MonthlyCashFlow:
    t: int
    collections: Decimal
    supplier_payments: Decimal
    payroll_payments: Decimal
    other_opex_payments: Decimal
    vat_paid: Decimal
    corp_tax_paid: Decimal
    operating_cash_flow: Decimal
    capex_paid: Decimal
    divestment_proceeds: Decimal
    investing_cash_flow: Decimal
    loan_drawdowns: Decimal
    loan_principal_repaid: Decimal
    loan_interest_paid: Decimal
    equity_injections: Decimal
    dividends_paid: Decimal
    origination_fees: Decimal
    financing_cash_flow: Decimal
    net_cash_flow: Decimal
    opening_cash: Decimal
    closing_cash: Decimal
    accounts_receivable: Decimal
    accounts_payable: Decimal


@dataclass(frozen=True)
class FinancingNeed:
    min_cash: Decimal
    min_cash_month: int
    max_shortfall_vs_policy: Decimal
    first_shortfall_month: int | None
    months_below_policy: int


def lag_months(days: int) -> int:
    """lag_months = floor(días / 30) — MOTOR §3.4."""
    return days // 30


def compute_financing_need(
    cash_flows: Sequence[MonthlyCashFlow],
    policy_min_cash: Decimal = ZERO,
) -> FinancingNeed:
    """MOTOR §11."""
    if not cash_flows:
        raise ValueError("cash_flows empty")

    min_cash = cash_flows[0].closing_cash
    min_cash_month = cash_flows[0].t
    max_shortfall = ZERO
    first_shortfall: int | None = None
    months_below = 0

    for cf in cash_flows:
        if cf.closing_cash < min_cash:
            min_cash = cf.closing_cash
            min_cash_month = cf.t
        shortfall = max(policy_min_cash - cf.closing_cash, ZERO)
        if shortfall > max_shortfall:
            max_shortfall = shortfall
        if shortfall > ZERO:
            months_below += 1
            if first_shortfall is None:
                first_shortfall = cf.t

    return FinancingNeed(
        min_cash=min_cash,
        min_cash_month=min_cash_month,
        max_shortfall_vs_policy=money(max_shortfall),
        first_shortfall_month=first_shortfall,
        months_below_policy=months_below,
    )


def _revenue_by_stream_month(
    streams: Sequence[RevenueStream],
    pnl: Sequence[MonthlyPnL],
) -> dict[str, list[Decimal]]:
    """Rebuild per-stream revenue from streams (source of truth for lags)."""
    from financetwin_engine.calc.pnl import revenue_for_stream

    horizon = len(pnl)
    out: dict[str, list[Decimal]] = {}
    for s in streams:
        out[s.id] = [revenue_for_stream(s, t) for t in range(horizon)]
    return out


def build_cash_flow_series(
    *,
    pnl: Sequence[MonthlyPnL],
    revenue_streams: Sequence[RevenueStream] = (),
    cost_items: Sequence[CostItem] = (),
    payroll: Sequence[PayrollLine] = (),
    opening_cash: Decimal = ZERO,
    vat_rate: Decimal = ZERO,
    default_purchase_payment_days: int = 30,
    loan_schedules: Sequence[LoanSchedule] = (),
    one_offs: Sequence[OneOffCashEvent] = (),
    capex_by_t: Sequence[Decimal] | None = None,
    corp_tax_paid_by_t: Sequence[Decimal] | None = None,
    vat_paid_by_t: Sequence[Decimal] | None = None,
) -> tuple[MonthlyCashFlow, ...]:
    """MOTOR §8 — caja mensual con lags y AR/AP simplificado."""
    horizon = len(pnl)
    if horizon < 1:
        raise ValueError("pnl series empty")

    rev_map = _revenue_by_stream_month(revenue_streams, pnl)

    # Precompute cost/payroll amounts by t (same as PnL)
    from financetwin_engine.calc.pnl import cost_item_amount, payroll_amount

    cost_by_id: dict[str, list[Decimal]] = {}
    for c in cost_items:
        cost_by_id[c.id] = [
            cost_item_amount(c, t, pnl[t].revenue) for t in range(horizon)
        ]

    payroll_by_id: dict[str, list[Decimal]] = {}
    for p in payroll:
        payroll_by_id[p.id] = [payroll_amount(p, t) for t in range(horizon)]

    # Loan aggregates by t
    drawdowns = [ZERO] * horizon
    principal_repaid = [ZERO] * horizon
    interest_paid = [ZERO] * horizon
    fees = [ZERO] * horizon
    for sched in loan_schedules:
        for row in sched.rows:
            if 0 <= row.t < horizon:
                drawdowns[row.t] += row.drawdown
                principal_repaid[row.t] += row.principal_repaid
                interest_paid[row.t] += row.interest_paid
                fees[row.t] += row.origination_fee_paid

    series: list[MonthlyCashFlow] = []
    cash = money(opening_cash)

    for t in range(horizon):
        collections = ZERO
        ar = ZERO
        for s in revenue_streams:
            lag_c = lag_months(s.collection_days)
            revs = rev_map[s.id]
            # collections at t from revenue at t - lag_c
            src = t - lag_c
            if src >= 0:
                collections += money(revs[src] * (ONE + vat_rate))
            # AR: accrued with VAT not yet collected: u = t-lag_c+1 .. t
            if lag_c > 0:
                for u in range(t - lag_c + 1, t + 1):
                    if u >= 0:
                        ar += money(revs[u] * (ONE + vat_rate))

        # COGS payments (company default purchase days)
        lag_cogs = lag_months(default_purchase_payment_days)
        supplier = ZERO
        ap = ZERO
        cogs_series = [p.cogs for p in pnl]
        src_cogs = t - lag_cogs
        if src_cogs >= 0:
            supplier += money(cogs_series[src_cogs] * (ONE + vat_rate))
        if lag_cogs > 0:
            for u in range(t - lag_cogs + 1, t + 1):
                if u >= 0:
                    ap += money(cogs_series[u] * (ONE + vat_rate))

        # CostItem payments (vatable in MVP)
        other_opex_pay = ZERO
        for c in cost_items:
            lag_p = lag_months(c.payment_days)
            amounts = cost_by_id[c.id]
            src = t - lag_p
            if src >= 0:
                pay = money(amounts[src] * (ONE + vat_rate))
                other_opex_pay += pay
                # COGS-like items aren't separate; all CostItems → other_opex_payments
            if lag_p > 0:
                for u in range(t - lag_p + 1, t + 1):
                    if u >= 0:
                        ap += money(amounts[u] * (ONE + vat_rate))

        payroll_pay = ZERO
        for p in payroll:
            lag_p = lag_months(p.payment_days)
            amounts = payroll_by_id[p.id]
            src = t - lag_p
            if src >= 0:
                payroll_pay += amounts[src]  # sin IVA

        vat_paid = ZERO
        if vat_paid_by_t is not None and t < len(vat_paid_by_t):
            vat_paid = vat_paid_by_t[t]

        corp_tax_paid = ZERO
        if corp_tax_paid_by_t is not None and t < len(corp_tax_paid_by_t):
            corp_tax_paid = corp_tax_paid_by_t[t]

        operating = money(
            collections
            - supplier
            - payroll_pay
            - other_opex_pay
            - vat_paid
            - corp_tax_paid
        )

        capex = ZERO
        if capex_by_t is not None and t < len(capex_by_t):
            capex = capex_by_t[t]

        equity = ZERO
        dividends = ZERO
        other_adjust = ZERO
        for ev in one_offs:
            if ev.t != t:
                continue
            if ev.kind == "equity_injection":
                equity += ev.amount
            elif ev.kind == "dividend":
                dividends += ev.amount
            elif ev.kind == "capex":
                # Si capex_by_t ya viene de compute_capex_by_t (incluye one_offs
                # kind=capex), no volver a sumar — anti doble conteo MOTOR §8.2.
                if capex_by_t is None:
                    capex += ev.amount
            elif ev.kind == "other_in":
                other_adjust += ev.amount
            elif ev.kind == "other_out":
                other_adjust -= ev.amount

        # other_in/out folded into operating for MVP simplicity
        operating = money(operating + other_adjust)

        investing = money(-capex)
        financing = money(
            drawdowns[t]
            - principal_repaid[t]
            - interest_paid[t]
            + equity
            - dividends
            - fees[t]
        )
        net = money(operating + investing + financing)
        opening = cash
        closing = money(opening + net)
        cash = closing

        series.append(
            MonthlyCashFlow(
                t=t,
                collections=money(collections),
                supplier_payments=money(supplier),
                payroll_payments=money(payroll_pay),
                other_opex_payments=money(other_opex_pay),
                vat_paid=money(vat_paid),
                corp_tax_paid=money(corp_tax_paid),
                operating_cash_flow=operating,
                capex_paid=money(capex),
                divestment_proceeds=ZERO,
                investing_cash_flow=investing,
                loan_drawdowns=money(drawdowns[t]),
                loan_principal_repaid=money(principal_repaid[t]),
                loan_interest_paid=money(interest_paid[t]),
                equity_injections=money(equity),
                dividends_paid=money(dividends),
                origination_fees=money(fees[t]),
                financing_cash_flow=financing,
                net_cash_flow=net,
                opening_cash=opening,
                closing_cash=closing,
                accounts_receivable=money(ar),
                accounts_payable=money(ap),
            )
        )

    return tuple(series)
