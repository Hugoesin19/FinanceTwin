"""Contrato común de Decision Packs — DECISION_PACKS §13."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Sequence

from financetwin_engine.mapper.build_ops import BuildOp


@dataclass(frozen=True)
class Issue:
    severity: Literal["error", "warning"]
    code: str
    message: str


@dataclass(frozen=True)
class PackInput:
    key: str
    label_ui: str
    value_type: str
    required: bool
    help_ui: str | None = None
    enum_values: tuple[str, ...] | None = None
    default_resolver: str | None = None


@dataclass(frozen=True)
class VariantPlan:
    name: str
    build_ops: tuple[BuildOp, ...]
    anchor_year_month: str
    horizon_months: int
    discount_rate_annual: Decimal
    auto_finance_deficits: bool = False
    open_year_month: str | None = None


@dataclass(frozen=True)
class BuiltScenarioBundle:
    pack_id: str
    variants: dict[str, VariantPlan]
    resolved_inputs: dict[str, Any] = field(default_factory=dict)


def has_errors(issues: Sequence[Issue]) -> bool:
    return any(i.severity == "error" for i in issues)
