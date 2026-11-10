"""Multi-criteria decision scorecard from pack metrics + optional Monte Carlo."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from financetwin_engine.calc.decimal_money import D


def _dec(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    return D(str(v))


def build_scorecard(
    *,
    investment_metrics: dict[str, Any] | None,
    financing_need: dict[str, Any] | None,
    policy_checks: list[dict[str, Any]] | None,
    montecarlo: dict[str, Any] | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Semáforo simple: valor / liquidez / deuda(runway) / riesgo(MC).
    No recalcula; solo clasifica campos del motor.
    """
    w = {
        "value": 0.35,
        "liquidity": 0.30,
        "debt": 0.15,
        "risk": 0.20,
        **(weights or {}),
    }
    im = investment_metrics or {}
    fn = financing_need or {}
    fails = sum(1 for p in (policy_checks or []) if p.get("status") == "fail")

    npv = _dec(im.get("npv"))
    if npv is None:
        value_label, value_pts = "—", 0.5
    elif npv >= 0:
        value_label, value_pts = "OK", 1.0
    else:
        value_label, value_pts = "Atención", 0.2

    months_below = int(fn.get("months_below_policy") or 0)
    if fails == 0 and months_below == 0:
        liq_label, liq_pts = "OK", 1.0
    elif fails == 0:
        liq_label, liq_pts = "Atención", 0.5
    else:
        liq_label, liq_pts = "Atención", 0.2

    shortfall = _dec(fn.get("max_shortfall_vs_policy")) or D(0)
    if shortfall <= 0 and months_below == 0:
        debt_label, debt_pts = "OK", 1.0
    elif months_below <= 2:
        debt_label, debt_pts = "Atención", 0.5
    else:
        debt_label, debt_pts = "Frágil", 0.2

    risk_label, risk_pts = "—", 0.5
    if montecarlo and montecarlo.get("prob_npv_positive") is not None:
        p = float(montecarlo["prob_npv_positive"])
        if p >= 0.7:
            risk_label, risk_pts = "OK", 1.0
        elif p >= 0.4:
            risk_label, risk_pts = "Atención", 0.5
        else:
            risk_label, risk_pts = "Frágil", 0.15

    score = (
        w["value"] * value_pts
        + w["liquidity"] * liq_pts
        + w["debt"] * debt_pts
        + w["risk"] * risk_pts
    )
    if score >= 0.75:
        overall = "Favorable"
    elif score >= 0.45:
        overall = "Mixto"
    else:
        overall = "Desfavorable"

    memo = (
        f"Valor={value_label}, liquidez={liq_label}, tensión caja={debt_label}, "
        f"riesgo MC={risk_label}. Semáforo: {overall}."
    )
    return {
        "valueScore": value_label,
        "liqScore": liq_label,
        "debtScore": debt_label,
        "riskScore": risk_label,
        "overall": overall,
        "score": round(score, 4),
        "weights": w,
        "memo": memo,
    }
