"""Bias / plan-vs-real — MODELO §8.3–8.4, DECISION_PACKS §2.6, VALIDACION V5."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from typing import Sequence

from financetwin_engine.calc.decimal_money import D

ZERO = D(0)
EPS = D("1e-12")

# MODELO §14 — catálogo canónico (no ampliar sin ADR)
CANONICAL_VARIABLE_KEYS: frozenset[str] = frozenset(
    {
        "sales_monthly",
        "gross_margin_pct",
        "capex_total",
        "rent_monthly",
        "headcount",
        "payroll_monthly",
        "min_cash",
        "payback_months",
        "revenue_ramp_month_to_breakeven",
    }
)

DECISION_PACK_IDS: frozenset[str] = frozenset(
    {
        "new_site",
        "financing",
        "asset_purchase",
        "hiring",
        "generic_investment",
        "liquidity_plan",
    }
)

DECISION_STATUSES: frozenset[str] = frozenset(
    {
        "draft",
        "approved",
        "rejected",
        "deferred",
        "executed",
        "cancelled",
    }
)


@dataclass(frozen=True)
class DeviationResult:
    deviation_pct: Decimal | None
    warning: str | None = None


@dataclass(frozen=True)
class BiasStats:
    n_observations: int
    median_bias: Decimal
    mean_bias: Decimal
    direction: str  # overestimate | underestimate | mixed
    confidence: str  # low | medium | high


def deviation_pct(forecast: Decimal | str | int, actual: Decimal | str | int) -> DeviationResult:
    """(forecast - actual) / forecast si forecast ≠ 0 — MODELO §13.7 / §2.6."""
    f = D(forecast)
    a = D(actual)
    if f == ZERO:
        if a != ZERO:
            return DeviationResult(None, "forecast=0 and actual≠0 → deviation_pct null")
        return DeviationResult(ZERO)
    return DeviationResult(D((f - a) / f))


def confidence_for_n(n: int) -> str:
    """Umbrales MODELO §8.4."""
    if n <= 0:
        return "low"
    if n <= 2:
        return "low"
    if n <= 9:
        return "medium"
    return "high"


def bias_direction(deviations: Sequence[Decimal]) -> str:
    if not deviations:
        return "mixed"
    pos = sum(1 for d in deviations if d > EPS)
    neg = sum(1 for d in deviations if d < -EPS)
    if pos and neg:
        return "mixed"
    if pos:
        return "overestimate"
    if neg:
        return "underestimate"
    return "mixed"


def compute_bias_stats(deviations: Sequence[Decimal]) -> BiasStats:
    if not deviations:
        raise ValueError("deviations empty")
    vals = [D(d) for d in deviations]
    med = D(median(vals))
    mean = D(sum(vals) / D(len(vals)))
    n = len(vals)
    return BiasStats(
        n_observations=n,
        median_bias=med,
        mean_bias=mean,
        direction=bias_direction(vals),
        confidence=confidence_for_n(n),
    )


def calibrate_value(user_value: Decimal | str | int, median_bias: Decimal | str) -> Decimal:
    """calibrated = user_value * (1 - median_bias) — DECISION_PACKS §2.6."""
    return D(user_value) * (D(1) - D(median_bias))


# Keys de ActualResult → input de pack cuando aplica calibración a inputs.
NEW_SITE_KEY_TO_INPUT: dict[str, str] = {
    "sales_monthly": "sales_run_rate",
    "gross_margin_pct": "gross_margin_pct",
    "capex_total": "capex_total",
    "rent_monthly": "rent_monthly",
    "headcount": "headcount",
}

PACK_KEY_TO_INPUT: dict[str, dict[str, str]] = {
    "new_site": NEW_SITE_KEY_TO_INPUT,
}


def key_to_input_for_pack(decision_pack_id: str) -> dict[str, str]:
    return dict(PACK_KEY_TO_INPUT.get(decision_pack_id) or {})


def offer_calibration(
    *,
    inputs: dict,
    profiles: Sequence[dict],
    key_to_input: dict[str, str] | None = None,
    min_n: int = 3,
) -> dict:
    """
    Ofrece inputs calibrados solo para keys con n_observations >= min_n.
    profiles: [{variable_key, n_observations, median_bias}, ...]
    """
    mapping = key_to_input if key_to_input is not None else NEW_SITE_KEY_TO_INPUT
    calibrated: dict = {}
    applied: list[dict] = []
    skipped: list[dict] = []

    if not mapping:
        return {
            "offered": False,
            "reason": "no calibration mapping for this pack",
            "calibrated_inputs": None,
            "applied": [],
            "skipped": [],
        }

    by_key = {p["variable_key"]: p for p in profiles}
    for var_key, input_key in mapping.items():
        if input_key not in inputs:
            continue
        prof = by_key.get(var_key)
        if prof is None:
            skipped.append({"variable_key": var_key, "reason": "no_profile"})
            continue
        n = int(prof["n_observations"])
        if n < min_n:
            skipped.append(
                {
                    "variable_key": var_key,
                    "reason": f"n_observations<{min_n}",
                    "n_observations": n,
                }
            )
            continue
        raw = inputs[input_key]
        cal = calibrate_value(raw, prof["median_bias"])
        if input_key == "headcount":
            from decimal import ROUND_HALF_UP

            calibrated[input_key] = str(int(cal.to_integral_value(rounding=ROUND_HALF_UP)))
        else:
            calibrated[input_key] = str(cal)
        applied.append(
            {
                "variable_key": var_key,
                "input_key": input_key,
                "n_observations": n,
                "median_bias": str(D(prof["median_bias"])),
                "user_value": str(raw),
                "calibrated_value": calibrated[input_key],
            }
        )

    offered = len(applied) > 0
    return {
        "offered": offered,
        "reason": None
        if offered
        else f"no keys with n_observations>={min_n} mappable to inputs",
        "calibrated_inputs": {**inputs, **calibrated} if offered else None,
        "applied": applied,
        "skipped": skipped,
    }
