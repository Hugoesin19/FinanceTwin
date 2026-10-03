"""Default resolvers — DECISION_PACKS §2.2 (subset used by new_site)."""

from __future__ import annotations

from decimal import Decimal
from statistics import median

from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot

ZERO = D(0)
ONE = D(1)


def linear_ramp(months: int) -> tuple[Decimal, ...]:
    """hist_ramp_or_linear fallback: lineal 0.25 → 1.0."""
    n = max(1, months)
    if n == 1:
        return (ONE,)
    start = D("0.25")
    return tuple(start + (ONE - start) * D(i) / D(n - 1) for i in range(n))


def avg_bu_revenue(snapshot: CompanyTwinSnapshot) -> Decimal | None:
    vals = [s.base_monthly_revenue for s in snapshot.revenue_streams]
    if not vals:
        return None
    return money_avg(vals)


def company_gross_margin(snapshot: CompanyTwinSnapshot) -> Decimal | None:
    streams = snapshot.revenue_streams
    if not streams:
        return None
    total_rev = sum((s.base_monthly_revenue for s in streams), ZERO)
    if total_rev == ZERO:
        return None
    weighted = sum(
        (s.base_monthly_revenue * s.gross_margin_pct for s in streams), ZERO
    )
    return weighted / total_rev


def avg_employer_cost(snapshot: CompanyTwinSnapshot) -> Decimal | None:
    vals = [p.monthly_employer_cost for p in snapshot.payroll]
    if not vals:
        return None
    return money_avg(vals)


def median_collection_days(snapshot: CompanyTwinSnapshot) -> int:
    vals = [s.collection_days for s in snapshot.revenue_streams]
    if not vals:
        return 30
    return int(median(vals))


def debt_cost_plus_premium(snapshot: CompanyTwinSnapshot) -> Decimal:
    rates = [L.annual_interest_rate for L in snapshot.loans]
    if not rates:
        return D("0.08")
    avg = sum(rates, ZERO) / D(len(rates))
    candidate = avg + D("0.02")
    floor = D("0.05")
    return candidate if candidate > floor else floor


def money_avg(vals: list[Decimal]) -> Decimal:
    return sum(vals, ZERO) / D(len(vals))
