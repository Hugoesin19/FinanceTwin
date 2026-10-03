"""Monthly P&L — MOTOR §5.1, §7.1–7.4, §9.2 (tax stub)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from financetwin_engine.calc.assets import depreciation_at
from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.model.asset import Asset
from financetwin_engine.model.costs import CostItem, PayrollLine
from financetwin_engine.model.revenue import RevenueStream

ZERO = D(0)
ONE = D(1)
TWELVE = D(12)


@dataclass(frozen=True)
class MonthlyPnL:
    t: int
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    payroll_expense: Decimal
    other_opex: Decimal
    ebitda: Decimal
    depreciation: Decimal
    ebit: Decimal
    interest_expense: Decimal
    ebt: Decimal
    corp_tax_expense: Decimal
    net_income: Decimal


def _active(start_t: int, end_t: int | None, t: int) -> bool:
    if t < start_t:
        return False
    if end_t is not None and t > end_t:
        return False
    return True


def _growth_factor(growth_annual: Decimal, start_t: int, t: int) -> Decimal:
    years = (t - start_t) // 12
    return (ONE + growth_annual) ** D(years)


def revenue_for_stream(stream: RevenueStream, t: int) -> Decimal:
    """MOTOR §7.1 — revenue base imponible."""
    if not _active(stream.start_t, stream.end_t, t):
        return ZERO
    growth = _growth_factor(stream.growth_annual, stream.start_t, t)
    idx = t - stream.start_t
    ramp = D(1)
    if stream.ramp is not None and 0 <= idx < len(stream.ramp):
        ramp = stream.ramp[idx]
    season = D(1)
    if stream.seasonality is not None and len(stream.seasonality) == 12:
        # calendar month within horizon: MVP uses t % 12 as seasonality index
        season = stream.seasonality[t % 12]
    return money(stream.base_monthly_revenue * growth * ramp * season)


def cogs_for_stream(stream: RevenueStream, revenue_s_t: Decimal) -> Decimal:
    """MOTOR §7.2."""
    return money(revenue_s_t * (ONE - stream.gross_margin_pct))


def cost_item_amount(
    item: CostItem,
    t: int,
    revenue_total_t: Decimal,
) -> Decimal:
    """MOTOR §7.3."""
    if not _active(item.start_t, item.end_t, t):
        return ZERO
    growth = _growth_factor(item.growth_annual, item.start_t, t)
    season = D(1)
    if item.seasonality is not None and len(item.seasonality) == 12:
        season = item.seasonality[t % 12]

    if item.nature == "fixed":
        if item.amount_monthly is None:
            raise ValueError(f"CostItem {item.id}: amount_monthly required for fixed")
        return money(item.amount_monthly * growth * season)

    if item.nature == "variable_pct_revenue":
        if item.pct_of_revenue is None:
            raise ValueError(f"CostItem {item.id}: pct_of_revenue required")
        return money(item.pct_of_revenue * revenue_total_t * season)

    raise ValueError(f"unsupported cost nature: {item.nature}")


def payroll_amount(line: PayrollLine, t: int) -> Decimal:
    if not _active(line.start_t, line.end_t, t):
        return ZERO
    return money(D(line.headcount) * line.monthly_employer_cost)


def assemble_monthly_pnl(
    *,
    t: int,
    revenue: Decimal,
    cogs: Decimal,
    payroll_expense: Decimal,
    other_opex: Decimal,
    depreciation: Decimal,
    interest_expense: Decimal,
    corp_tax_rate: Decimal = ZERO,
) -> MonthlyPnL:
    """Construye MonthlyPnL a partir de agregados del mes — MOTOR §5.1."""
    gross_profit = money(revenue - cogs)
    ebitda = money(gross_profit - payroll_expense - other_opex)
    ebit = money(ebitda - depreciation)
    ebt = money(ebit - interest_expense)
    # §9.2 simplificado: tax on positive ebt only (sin NOL aquí)
    tax_base = ebt if ebt > ZERO else ZERO
    corp_tax_expense = money(tax_base * corp_tax_rate)
    net_income = money(ebt - corp_tax_expense)
    return MonthlyPnL(
        t=t,
        revenue=money(revenue),
        cogs=money(cogs),
        gross_profit=gross_profit,
        payroll_expense=money(payroll_expense),
        other_opex=money(other_opex),
        ebitda=ebitda,
        depreciation=money(depreciation),
        ebit=ebit,
        interest_expense=money(interest_expense),
        ebt=ebt,
        corp_tax_expense=corp_tax_expense,
        net_income=net_income,
    )


def build_pnl_series(
    *,
    horizon: int,
    revenue_streams: Sequence[RevenueStream] = (),
    cost_items: Sequence[CostItem] = (),
    payroll: Sequence[PayrollLine] = (),
    assets: Sequence[Asset] = (),
    interest_expense_by_t: Sequence[Decimal] | None = None,
    corp_tax_rate: Decimal = ZERO,
) -> tuple[MonthlyPnL, ...]:
    """P&L mensual para t=0..H-1."""
    series: list[MonthlyPnL] = []
    for t in range(horizon):
        revenue = ZERO
        cogs = ZERO
        for s in revenue_streams:
            rev_s = revenue_for_stream(s, t)
            revenue += rev_s
            cogs += cogs_for_stream(s, rev_s)

        other_opex = ZERO
        for c in cost_items:
            other_opex += cost_item_amount(c, t, revenue)

        payroll_expense = ZERO
        for p in payroll:
            payroll_expense += payroll_amount(p, t)

        depreciation = ZERO
        for a in assets:
            depreciation += depreciation_at(a, t)

        interest = ZERO
        if interest_expense_by_t is not None and t < len(interest_expense_by_t):
            interest = interest_expense_by_t[t]

        series.append(
            assemble_monthly_pnl(
                t=t,
                revenue=revenue,
                cogs=cogs,
                payroll_expense=payroll_expense,
                other_opex=other_opex,
                depreciation=depreciation,
                interest_expense=interest,
                corp_tax_rate=corp_tax_rate,
            )
        )
    return tuple(series)
