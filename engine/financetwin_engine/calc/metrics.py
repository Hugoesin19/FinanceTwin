"""Investment metrics — MOTOR §10, API §16."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException, Overflow, DivisionByZero
from typing import Sequence

from financetwin_engine.calc.decimal_money import D, money

ZERO = D(0)
ONE = D(1)
TWELVE = D(12)


@dataclass(frozen=True)
class InvestmentMetrics:
    """Métricas de inversión (VAN, TIR, payback)."""

    npv: Decimal
    irr_annual: Decimal | None
    payback_simple: int | None
    payback_discounted: int | None
    warnings: tuple[str, ...] = ()


def monthly_discount_rate(discount_rate_annual: Decimal) -> Decimal:
    """r_month = (1 + r_annual)^(1/12) - 1 — MOTOR §10.2."""
    return (ONE + discount_rate_annual) ** (ONE / TWELVE) - ONE


def calculate_npv(
    cash_flows: Sequence[Decimal],
    discount_rate_annual: Decimal,
) -> Decimal:
    """VAN = Σ FC_t / (1 + r_month)^t — MOTOR §10.2."""
    r_month = monthly_discount_rate(discount_rate_annual)
    total = ZERO
    for t, fc in enumerate(cash_flows):
        total += fc / ((ONE + r_month) ** t)
    return money(total)


def calculate_payback_simple(cash_flows: Sequence[Decimal]) -> int | None:
    """Menor T tal que Σ_{t=0..T} FC_t >= 0 — MOTOR §10.4."""
    cumulative = ZERO
    for t, fc in enumerate(cash_flows):
        cumulative += fc
        if cumulative >= ZERO:
            return t
    return None


def calculate_payback_discounted(
    cash_flows: Sequence[Decimal],
    discount_rate_annual: Decimal,
) -> int | None:
    """Menor T tal que Σ FC_t / (1+r_month)^t >= 0 — MOTOR §10.4."""
    r_month = monthly_discount_rate(discount_rate_annual)
    cumulative = ZERO
    for t, fc in enumerate(cash_flows):
        cumulative += fc / ((ONE + r_month) ** t)
        if cumulative >= ZERO:
            return t
    return None


def _has_sign_change(cash_flows: Sequence[Decimal]) -> bool:
    nonzero = [fc for fc in cash_flows if fc != ZERO]
    if len(nonzero) < 2:
        return False
    for a, b in zip(nonzero, nonzero[1:]):
        if (a > ZERO) != (b > ZERO):
            return True
    return False


def _npv_at_monthly_rate(cash_flows: Sequence[Decimal], y: Decimal) -> Decimal:
    total = ZERO
    for t, fc in enumerate(cash_flows):
        denom = (ONE + y) ** t
        if denom == ZERO:
            raise Overflow("discount factor underflow")
        total += fc / denom
    return total


def _npv_derivative(cash_flows: Sequence[Decimal], y: Decimal) -> Decimal:
    total = ZERO
    for t, fc in enumerate(cash_flows):
        if t == 0:
            continue
        denom = (ONE + y) ** (t + 1)
        if denom == ZERO:
            raise Overflow("discount factor underflow")
        total -= D(t) * fc / denom
    return total


def _solve_irr_monthly(cash_flows: Sequence[Decimal]) -> Decimal | None:
    """Newton-Raphson con fallback a bisección — MOTOR §10.3."""
    try:
        y = D("0.01")
        for _ in range(100):
            f = _npv_at_monthly_rate(cash_flows, y)
            if abs(f) < D("1e-12"):
                return y
            df = _npv_derivative(cash_flows, y)
            if df == ZERO:
                break
            y_next = y - f / df
            if y_next <= D("-0.999999"):
                break
            if abs(y_next - y) < D("1e-14"):
                return y_next
            y = y_next

        # Bisección en (-0.99, 10)
        lo, hi = D("-0.99"), D(10)
        f_lo = _npv_at_monthly_rate(cash_flows, lo)
        f_hi = _npv_at_monthly_rate(cash_flows, hi)
        if f_lo * f_hi > ZERO:
            return None
        for _ in range(200):
            mid = (lo + hi) / D(2)
            f_mid = _npv_at_monthly_rate(cash_flows, mid)
            if abs(f_mid) < D("1e-12") or abs(hi - lo) < D("1e-14"):
                return mid
            if f_lo * f_mid <= ZERO:
                hi = mid
                f_hi = f_mid
            else:
                lo = mid
                f_lo = f_mid
        return (lo + hi) / D(2)
    except (Overflow, DivisionByZero, DecimalException, ZeroDivisionError):
        return None


def calculate_irr_annual(
    cash_flows: Sequence[Decimal],
) -> tuple[Decimal | None, tuple[str, ...]]:
    """TIR anual = (1 + y)^12 - 1; undefined si no hay cambio de signo."""
    if not _has_sign_change(cash_flows):
        return None, ("TIR undefined: no sign change in cash flows",)

    y = _solve_irr_monthly(cash_flows)
    if y is None:
        return None, ("TIR undefined: solver did not converge",)

    try:
        irr_annual = (ONE + y) ** TWELVE - ONE
    except (Overflow, DecimalException):
        return None, ("TIR undefined: annualization overflow",)
    return irr_annual, ()


def calculate_investment_metrics(
    cash_flows: Sequence[Decimal],
    discount_rate_annual: Decimal,
) -> InvestmentMetrics:
    """Utilidad pura testeable sin modelo completo — MOTOR §16."""
    if any(isinstance(fc, float) for fc in cash_flows):
        raise TypeError("cash_flows must use Decimal, not float")
    if isinstance(discount_rate_annual, float):
        raise TypeError("discount_rate_annual must use Decimal, not float")

    flows = tuple(D(fc) if not isinstance(fc, Decimal) else fc for fc in cash_flows)
    rate = (
        discount_rate_annual
        if isinstance(discount_rate_annual, Decimal)
        else D(discount_rate_annual)
    )

    npv = calculate_npv(flows, rate)
    irr_annual, irr_warnings = calculate_irr_annual(flows)
    payback_simple = calculate_payback_simple(flows)
    payback_discounted = calculate_payback_discounted(flows, rate)

    return InvestmentMetrics(
        npv=npv,
        irr_annual=irr_annual,
        payback_simple=payback_simple,
        payback_discounted=payback_discounted,
        warnings=irr_warnings,
    )
