"""Decimal money helpers — MOTOR §3.3, principio M2."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP, getcontext

# Cálculos intermedios: precisión Decimal alta (mín. 28 dígitos)
getcontext().prec = max(getcontext().prec, 28)

MONEY_QUANT = Decimal("0.01")


def D(value: str | int | Decimal) -> Decimal:
    """Construye Decimal sin pasar por float."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    """Redondeo final de importes: ROUND_HALF_UP a 2 decimales."""
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
