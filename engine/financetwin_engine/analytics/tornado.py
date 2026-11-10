"""Tornado chart — impact ranking from ±delta pack re-runs (no homemade NPV)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from financetwin_engine.analytics.sensitivity import (
    DEFAULT_DIRECT_DELTAS,
    MetricView,
    _d,
    _set_input,
    metric_view_to_dict,
    metrics_from_pack_run,
    run_pack_variant,
)
from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot

ZERO = D(0)
ONE = D(1)


def _metric_pick(m: MetricView, metric: str) -> Decimal | None:
    if metric == "npv":
        return m.npv
    if metric == "min_cash":
        return m.min_cash
    raise ValueError(f"unsupported tornado metric: {metric}")


def run_tornado(
    pack: Any,
    snapshot: CompanyTwinSnapshot,
    inputs: dict[str, Any],
    *,
    variant: str = "base",
    metric: str = "npv",
    deltas: tuple[Decimal, ...] = DEFAULT_DIRECT_DELTAS,
) -> dict[str, Any]:
    plan = pack.analysis_plan() if hasattr(pack, "analysis_plan") else {}
    vars_ = list(plan.get("sensitivity_vars") or [])
    if not vars_:
        raise ValueError("pack has no sensitivity_vars for tornado")

    resolved, base_pr = run_pack_variant(pack, snapshot, inputs, variant=variant)
    base_m = metrics_from_pack_run(base_pr)
    base_val = _metric_pick(base_m, metric)

    bars: list[dict[str, Any]] = []
    for var in vars_:
        if var not in resolved:
            bars.append({"variable": var, "skipped": True, "reason": "missing input"})
            continue
        base_input = _d(resolved[var])
        low_m: MetricView | None = None
        high_m: MetricView | None = None
        low_delta = min(deltas)
        high_delta = max(deltas)
        for delta in (low_delta, high_delta):
            new_val = money(base_input * (ONE + delta))
            if var == "gross_margin_pct":
                new_val = min(ONE, max(ZERO, new_val))
            elif var == "loan_annual_rate":
                new_val = max(ZERO, new_val)
            trial = _set_input(resolved, var, str(new_val))
            if var == "capex_total" and "equity_amount" in resolved and "debt_amount" in resolved:
                debt = _d(resolved.get("debt_amount"), ZERO)
                trial["equity_amount"] = str(max(ZERO, new_val - debt))
            _, pr = run_pack_variant(pack, snapshot, trial, variant=variant)
            m = metrics_from_pack_run(pr)
            if delta == low_delta:
                low_m = m
            else:
                high_m = m
        assert low_m is not None and high_m is not None
        v_lo = _metric_pick(low_m, metric)
        v_hi = _metric_pick(high_m, metric)
        span = None
        if v_lo is not None and v_hi is not None:
            span = abs(v_hi - v_lo)
        bars.append(
            {
                "variable": var,
                "skipped": False,
                "metric": metric,
                "low_delta": str(low_delta),
                "high_delta": str(high_delta),
                "metric_at_low": None if v_lo is None else str(v_lo),
                "metric_at_high": None if v_hi is None else str(v_hi),
                "impact_span": None if span is None else str(span),
                "metrics_low": metric_view_to_dict(low_m),
                "metrics_high": metric_view_to_dict(high_m),
            }
        )

    ranked = sorted(
        [b for b in bars if not b.get("skipped") and b.get("impact_span") is not None],
        key=lambda b: D(str(b["impact_span"])),
        reverse=True,
    )
    return {
        "kind": "tornado",
        "variant": variant,
        "metric": metric,
        "base": metric_view_to_dict(base_m),
        "base_metric": None if base_val is None else str(base_val),
        "bars": ranked + [b for b in bars if b.get("skipped")],
    }
