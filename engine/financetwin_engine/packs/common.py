"""Helpers compartidos de packs — DECISION_PACKS."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper.build_ops import BuildOp

ZERO = D(0)
ONE = D(1)


def d(value: Any, default: Decimal | None = None) -> Decimal:
    if value is None:
        if default is not None:
            return default
        raise ValueError("missing money/rate value")
    if isinstance(value, float):
        raise TypeError("float not allowed in pack inputs")
    return D(value)


def stable_id(kind: str, name: str, variant: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "x"
    return f"{kind}-{slug[:32]}-{variant}"


def savings_ops(
    *,
    opex_savings_monthly: Decimal,
    cost_item_id_to_reduce: str | None,
    current_amount: Decimal | None,
    name_prefix: str,
    start_year_month: str,
    variant: str,
) -> tuple[list[BuildOp], list[str]]:
    """
    MODELO §2.5 — ahorros sin CostItem negativo.
    Returns (ops, warnings).
    """
    ops: list[BuildOp] = []
    warnings: list[str] = []
    if opex_savings_monthly <= ZERO:
        return ops, warnings

    if cost_item_id_to_reduce and current_amount is not None:
        new_amt = max(ZERO, current_amount - opex_savings_monthly)
        ops.append(
            BuildOp(
                op="set_field",
                entity_type="cost_items",
                entity_id=cost_item_id_to_reduce,
                field="amount_monthly",
                value=str(new_amt),
            )
        )
        return ops, warnings

    # §2.5.3 — RevenueStream equivalente
    rid = stable_id("rev-savings", name_prefix, variant)
    ops.append(
        BuildOp(
            op="add_entity",
            entity_type="revenue_streams",
            entity_id=rid,
            payload={
                "id": rid,
                "name": "Ahorro opex (equivalente)",
                "revenue_type": "recurring",
                "start_year_month": start_year_month,
                "base_monthly_revenue": str(opex_savings_monthly),
                "gross_margin_pct": "1.0",
                "collection_days": 0,
                "growth_annual": "0",
                "origin": "calculated",
                "confidence": "medium",
            },
        )
    )
    warnings.append(
        "opex_savings modeled as equivalent revenue stream (gross_margin=1); not a negative cost"
    )
    return ops, warnings
