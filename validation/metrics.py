"""Helpers F8 — métricas VALIDACION §6 / §13 (sin float intermedio)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from financetwin_engine.calc.decimal_money import D

EPS = D("1.00")
MONEY_Q = D("0.01")


def money_local(value: Decimal) -> Decimal:
    return value.quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def ape(pred: Decimal | str | int, real: Decimal | str | int) -> Decimal:
    p, r = D(pred), D(real)
    denom = abs(r) if abs(r) >= EPS else EPS
    return abs(p - r) / denom


def mape(preds: Sequence[Decimal | str | int], reals: Sequence[Decimal | str | int]) -> Decimal:
    if len(preds) != len(reals) or not preds:
        raise ValueError("preds/reals length mismatch or empty")
    total = D(0)
    for p, r in zip(preds, reals):
        total += ape(p, r)
    return total / D(len(preds))


def relative_bias(
    preds: Sequence[Decimal | str | int], reals: Sequence[Decimal | str | int]
) -> Decimal:
    if len(preds) != len(reals) or not preds:
        raise ValueError("preds/reals length mismatch or empty")
    total = D(0)
    for p, r in zip(preds, reals):
        pp, rr = D(p), D(r)
        denom = abs(rr) if abs(rr) >= EPS else EPS
        total += (pp - rr) / denom
    return total / D(len(preds))


def independent_npv(
    cash_flows: Sequence[Decimal | str | int], discount_rate_annual: Decimal | str
) -> Decimal:
    """VAN independiente (no usa calculate_investment_metrics)."""
    r_annual = D(discount_rate_annual)
    r_month = (D(1) + r_annual) ** (D(1) / D(12)) - D(1)
    total = D(0)
    for t, fc in enumerate(cash_flows):
        total += D(fc) / ((D(1) + r_month) ** t)
    return money_local(total)


def independent_french_payment(
    principal: Decimal | str, annual_rate: Decimal | str, term_months: int
) -> Decimal:
    """Cuota francesa independiente (TIN/12)."""
    p, i = D(principal), D(annual_rate) / D(12)
    n = D(term_months)
    if i == 0:
        return money_local(p / n)
    return money_local(p * i / (D(1) - (D(1) + i) ** (-n)))
