"""Sensibilidad / inversa / stress — MOTOR M8 + DECISION_PACKS §5.5.

Orquestación pura: clona inputs, llama pack.build + calculate(); no recalcula a mano.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot
from financetwin_engine.mapper.time import add_months
from financetwin_engine.packs.base import Issue, has_errors
from financetwin_engine.packs.runner import run_variant

ZERO = D(0)
ONE = D(1)


class PackLike(Protocol):
    id: str

    def analysis_plan(self) -> dict[str, Any]: ...

    def resolve_defaults(
        self, snapshot: CompanyTwinSnapshot, user_partial: dict[str, Any]
    ) -> dict[str, Any]: ...

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]: ...

    def build(self, snapshot: CompanyTwinSnapshot, inputs: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class MetricView:
    npv: Decimal | None
    irr_annual: Decimal | None
    payback_simple: int | None
    payback_discounted: int | None
    min_cash: Decimal
    min_cash_month: int
    max_shortfall_vs_policy: Decimal
    first_shortfall_month: int | None
    months_below_policy: int
    result_hash: str
    inputs_hash: str


def metrics_from_pack_run(pr: Any) -> MetricView:
    result = pr.result
    im = result.investment_metrics
    fn = result.financing_need
    assert fn is not None
    return MetricView(
        npv=None if im is None else im.npv,
        irr_annual=None if im is None else im.irr_annual,
        payback_simple=None if im is None else im.payback_simple,
        payback_discounted=None if im is None else im.payback_discounted,
        min_cash=fn.min_cash,
        min_cash_month=fn.min_cash_month,
        max_shortfall_vs_policy=fn.max_shortfall_vs_policy,
        first_shortfall_month=fn.first_shortfall_month,
        months_below_policy=fn.months_below_policy,
        result_hash=result.result_hash,
        inputs_hash=pr.mapped.inputs_hash,
    )


def metric_view_to_dict(m: MetricView) -> dict[str, Any]:
    return {
        "npv": None if m.npv is None else str(m.npv),
        "irr_annual": None if m.irr_annual is None else str(m.irr_annual),
        "payback_simple": m.payback_simple,
        "payback_discounted": m.payback_discounted,
        "min_cash": str(m.min_cash),
        "min_cash_month": m.min_cash_month,
        "max_shortfall_vs_policy": str(m.max_shortfall_vs_policy),
        "first_shortfall_month": m.first_shortfall_month,
        "months_below_policy": m.months_below_policy,
        "result_hash": m.result_hash,
        "inputs_hash": m.inputs_hash,
    }


def _d(v: Any, default: Decimal | None = None) -> Decimal:
    if v is None:
        if default is None:
            raise ValueError("missing decimal")
        return default
    if isinstance(v, Decimal):
        return v
    return D(str(v))


def run_pack_variant(
    pack: PackLike,
    snapshot: CompanyTwinSnapshot,
    inputs: dict[str, Any],
    *,
    variant: str = "base",
) -> tuple[dict[str, Any], Any]:
    resolved = pack.resolve_defaults(snapshot, deepcopy(inputs))
    issues = pack.validate_inputs(resolved)
    if has_errors(issues):
        msgs = [i.message for i in issues if i.severity == "error"]
        raise ValueError("; ".join(msgs) or "pack validation failed")
    bundle = pack.build(snapshot, resolved)
    if variant not in bundle.variants:
        raise ValueError(f"unknown variant {variant!r}; have {list(bundle.variants)}")
    return resolved, run_variant(snapshot, bundle.variants[variant])


def _set_input(inputs: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    out = deepcopy(inputs)
    out[key] = value
    return out


def _policy_min_cash(snapshot: CompanyTwinSnapshot) -> Decimal:
    return snapshot.policies.min_cash


def _metric_value(view: MetricView, metric: str) -> Decimal:
    if metric == "npv":
        if view.npv is None:
            raise ValueError("npv not available for this run")
        return view.npv
    if metric == "min_cash":
        return view.min_cash
    raise ValueError(f"unsupported metric for inverse: {metric}")


def _resolve_threshold(
    snapshot: CompanyTwinSnapshot, threshold: str, metric: str
) -> Decimal:
    if threshold == "policy.min_cash":
        return _policy_min_cash(snapshot)
    return _d(threshold)


DEFAULT_DIRECT_DELTAS: tuple[Decimal, ...] = (D("-0.10"), D("0.10"))


def direct_sensitivity(
    pack: PackLike,
    snapshot: CompanyTwinSnapshot,
    inputs: dict[str, Any],
    *,
    variant: str = "base",
    deltas: tuple[Decimal, ...] = DEFAULT_DIRECT_DELTAS,
) -> dict[str, Any]:
    plan = pack.analysis_plan()
    vars_ = list(plan.get("sensitivity_vars") or [])
    if not vars_:
        raise ValueError("pack has no sensitivity_vars in analysis_plan")

    resolved, base_pr = run_pack_variant(pack, snapshot, inputs, variant=variant)
    base_m = metrics_from_pack_run(base_pr)
    rows: list[dict[str, Any]] = []
    for var in vars_:
        if var not in resolved:
            rows.append(
                {
                    "variable": var,
                    "skipped": True,
                    "reason": "variable not in resolved inputs",
                }
            )
            continue
        base_val = _d(resolved[var])
        for delta in deltas:
            new_val = money(base_val * (ONE + delta))
            if var == "gross_margin_pct":
                new_val = min(ONE, max(ZERO, new_val))
            elif var == "loan_annual_rate":
                new_val = max(ZERO, new_val)
            trial_inputs = _set_input(resolved, var, str(new_val))
            # keep funding identity for new_site-like packs when capex changes
            if var == "capex_total" and "equity_amount" in resolved and "debt_amount" in resolved:
                debt = _d(resolved.get("debt_amount"), ZERO)
                trial_inputs["equity_amount"] = str(max(ZERO, new_val - debt))
            _, pr = run_pack_variant(pack, snapshot, trial_inputs, variant=variant)
            m = metrics_from_pack_run(pr)
            rows.append(
                {
                    "variable": var,
                    "skipped": False,
                    "base_value": str(base_val),
                    "delta_pct": str(delta),
                    "trial_value": str(new_val),
                    "metrics": metric_view_to_dict(m),
                }
            )
    return {
        "kind": "direct",
        "variant": variant,
        "base": metric_view_to_dict(base_m),
        "rows": rows,
    }


def _binary_search_input(
    *,
    pack: PackLike,
    snapshot: CompanyTwinSnapshot,
    base_inputs: dict[str, Any],
    variable: str,
    metric: str,
    threshold: Decimal,
    variant: str,
    low: Decimal,
    high: Decimal,
    maximize_metric_with_input: bool,
    max_iter: int = 40,
    tol: Decimal = D("0.01"),
) -> dict[str, Any]:
    """Busca valor de `variable` tal que metric ≈ threshold (Decimal, sin float)."""

    def eval_at(x: Decimal) -> MetricView:
        trial = _set_input(base_inputs, variable, str(money(x)))
        if variable == "capex_total" and "debt_amount" in base_inputs:
            debt = _d(base_inputs.get("debt_amount"), ZERO)
            trial["equity_amount"] = str(max(ZERO, money(x) - debt))
        _, pr = run_pack_variant(pack, snapshot, trial, variant=variant)
        return metrics_from_pack_run(pr)

    lo, hi = low, high
    m_lo = eval_at(lo)
    m_hi = eval_at(hi)
    v_lo = _metric_value(m_lo, metric)
    v_hi = _metric_value(m_hi, metric)

    # Ensure bracket if possible by expanding once
    if maximize_metric_with_input:
        # metric increases with input → want v_lo <= thr <= v_hi ideally
        crosses = (v_lo - threshold) * (v_hi - threshold) <= ZERO
    else:
        crosses = (v_lo - threshold) * (v_hi - threshold) <= ZERO

    if not crosses:
        return {
            "variable": variable,
            "metric": metric,
            "threshold": str(threshold),
            "found": False,
            "reason": "no_bracket",
            "low": str(lo),
            "high": str(hi),
            "metric_at_low": str(v_lo),
            "metric_at_high": str(v_hi),
        }

    best_x = hi
    best_m = m_hi
    for _ in range(max_iter):
        mid = money((lo + hi) / D(2))
        m_mid = eval_at(mid)
        v_mid = _metric_value(m_mid, metric)
        best_x, best_m = mid, m_mid
        if abs(v_mid - threshold) <= tol:
            break
        if maximize_metric_with_input:
            # higher x → higher metric
            if v_mid < threshold:
                lo = mid
            else:
                hi = mid
        else:
            if v_mid > threshold:
                lo = mid
            else:
                hi = mid
        if abs(hi - lo) <= tol:
            break

    v_best = _metric_value(best_m, metric)
    # tol práctico: abs + relativo (VAN/caja en €)
    eff_tol = max(tol, abs(threshold) * D("0.001") + D("1"))
    close = abs(v_best - threshold) <= eff_tol
    return {
        "variable": variable,
        "metric": metric,
        "threshold": str(threshold),
        "found": bool(close),
        "value": str(best_x),
        "metric_at_value": str(v_best),
        "metrics": metric_view_to_dict(best_m),
        **({} if close else {"reason": "approx_not_within_tol"}),
    }


def inverse_sensitivity(
    pack: PackLike,
    snapshot: CompanyTwinSnapshot,
    inputs: dict[str, Any],
    *,
    variant: str = "base",
) -> dict[str, Any]:
    plan = pack.analysis_plan()
    specs = list(plan.get("inverse_sensitivity") or [])
    if not specs:
        raise ValueError("pack has no inverse_sensitivity in analysis_plan")

    resolved, base_pr = run_pack_variant(pack, snapshot, inputs, variant=variant)
    base_m = metrics_from_pack_run(base_pr)
    results: list[dict[str, Any]] = []

    for spec in specs:
        metric = spec["metric"]
        threshold = _resolve_threshold(snapshot, str(spec["threshold"]), metric)
        for var in spec.get("vs") or []:
            if var not in resolved:
                results.append(
                    {
                        "variable": var,
                        "metric": metric,
                        "found": False,
                        "reason": "variable not in resolved inputs",
                    }
                )
                continue
            base_val = _d(resolved[var])
            # brackets
            if var in ("gross_margin_pct", "loan_annual_rate") or var.endswith("_pct"):
                low = ZERO
                high = ONE if var == "gross_margin_pct" else money(base_val + D("0.20"))
                if var == "loan_annual_rate":
                    high = max(high, money(base_val * D("3")))
                maximize = metric != "npv" or var != "capex_total"
                if metric == "npv" and var == "gross_margin_pct":
                    maximize = True
                elif metric == "npv" and var == "loan_annual_rate":
                    maximize = False  # higher rate → lower npv typically
            elif metric == "npv" and var == "capex_total":
                # lower capex → higher npv typically
                low = max(ZERO, money(base_val * D("0.05")))
                high = money(base_val * D("3"))
                maximize = False
            elif metric == "npv":
                low = max(ZERO, money(base_val * D("0.05")))
                high = money(base_val * D("3"))
                maximize = True
            elif metric == "min_cash":
                low = max(ZERO, money(base_val * D("0.05")))
                high = money(base_val * D("3"))
                maximize = True  # more sales → higher min_cash typically
            else:
                low = max(ZERO, money(base_val * D("0.1")))
                high = money(base_val * D("2"))
                maximize = True

            if low >= high:
                results.append(
                    {
                        "variable": var,
                        "metric": metric,
                        "found": False,
                        "reason": "invalid_bracket",
                        "low": str(low),
                        "high": str(high),
                    }
                )
                continue

            results.append(
                _binary_search_input(
                    pack=pack,
                    snapshot=snapshot,
                    base_inputs=resolved,
                    variable=var,
                    metric=metric,
                    threshold=threshold,
                    variant=variant,
                    low=low,
                    high=high,
                    maximize_metric_with_input=maximize,
                )
            )

    return {
        "kind": "inverse",
        "variant": variant,
        "base": metric_view_to_dict(base_m),
        "rows": results,
    }


def _apply_stress(
    resolved: dict[str, Any], name: str
) -> tuple[dict[str, Any], str | None]:
    out = deepcopy(resolved)
    if name == "sales_-15pct":
        out["sales_run_rate"] = str(money(_d(out["sales_run_rate"]) * D("0.85")))
        return out, None
    if name == "sales_-30pct":
        out["sales_run_rate"] = str(money(_d(out["sales_run_rate"]) * D("0.70")))
        return out, None
    if name == "open_plus_2m":
        out["open_year_month"] = add_months(str(out["open_year_month"]), 2)
        return out, None
    if name == "open_plus_4m":
        out["open_year_month"] = add_months(str(out["open_year_month"]), 4)
        return out, None
    if name == "rate_plus_200bp":
        if "loan_annual_rate" not in out:
            return out, "loan_annual_rate missing"
        out["loan_annual_rate"] = str(money(_d(out["loan_annual_rate"]) + D("0.02")))
        return out, None
    return out, f"unknown stress {name!r}"


def stress_tests(
    pack: PackLike,
    snapshot: CompanyTwinSnapshot,
    inputs: dict[str, Any],
    *,
    variant: str = "base",
) -> dict[str, Any]:
    plan = pack.analysis_plan()
    names = list(plan.get("stress_tests") or [])
    if not names:
        raise ValueError("pack has no stress_tests in analysis_plan")

    resolved, base_pr = run_pack_variant(pack, snapshot, inputs, variant=variant)
    base_m = metrics_from_pack_run(base_pr)
    rows: list[dict[str, Any]] = []
    for name in names:
        trial, skip = _apply_stress(resolved, name)
        if skip:
            rows.append({"stress": name, "skipped": True, "reason": skip})
            continue
        _, pr = run_pack_variant(pack, snapshot, trial, variant=variant)
        rows.append(
            {
                "stress": name,
                "skipped": False,
                "metrics": metric_view_to_dict(metrics_from_pack_run(pr)),
            }
        )
    return {
        "kind": "stress",
        "variant": variant,
        "base": metric_view_to_dict(base_m),
        "rows": rows,
    }


def run_analysis(
    pack: PackLike,
    snapshot: CompanyTwinSnapshot,
    inputs: dict[str, Any],
    *,
    variant: str = "base",
    include: tuple[str, ...] = ("direct", "inverse", "stress"),
) -> dict[str, Any]:
    """Ejecuta bloques solicitados del analysis_plan del pack."""
    if not hasattr(pack, "analysis_plan"):
        raise ValueError(f"pack {getattr(pack, 'id', '?')!r} has no analysis_plan")
    plan = pack.analysis_plan()
    if not plan.get("sensitivity_vars") and not plan.get("inverse_sensitivity"):
        raise ValueError(f"pack {pack.id!r} analysis_plan empty")

    out: dict[str, Any] = {
        "pack_id": pack.id,
        "variant": variant,
        "analysis_plan": {
            "sensitivity_vars": plan.get("sensitivity_vars") or [],
            "inverse_sensitivity": plan.get("inverse_sensitivity") or [],
            "stress_tests": plan.get("stress_tests") or [],
        },
    }
    if "direct" in include:
        out["direct"] = direct_sensitivity(
            pack, snapshot, inputs, variant=variant
        )
    if "inverse" in include:
        out["inverse"] = inverse_sensitivity(
            pack, snapshot, inputs, variant=variant
        )
    if "stress" in include:
        out["stress"] = stress_tests(pack, snapshot, inputs, variant=variant)
    return out
