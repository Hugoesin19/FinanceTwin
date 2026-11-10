"""Monte Carlo over pack runs — deterministic seed; reuses L0 via pack runner."""

from __future__ import annotations

import random
from copy import deepcopy
from decimal import Decimal
from typing import Any

from financetwin_engine.analytics.sensitivity import MetricView, metrics_from_pack_run, run_pack_variant
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot


def _percentile(sorted_vals: list[Decimal], p: float) -> Decimal | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = int(round((len(sorted_vals) - 1) * p))
    idx = max(0, min(len(sorted_vals) - 1, idx))
    return sorted_vals[idx]


def run_montecarlo(
    *,
    pack: Any,
    snapshot: CompanyTwinSnapshot,
    base_inputs: dict[str, Any],
    variant: str = "base",
    ranges: dict[str, dict[str, str]] | None = None,
    n_sims: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    """
    ranges: { input_key: {"low": "0.9", "high": "1.1"} } multiplicative factors,
    or {"mode":"absolute","min":"...","max":"..."}.
    """
    rng = random.Random(seed)
    npvs: list[Decimal] = []
    breaches = 0
    positive = 0
    skipped = 0
    n = max(1, int(n_sims))

    for _ in range(n):
        inputs = deepcopy(base_inputs)
        for key, spec in (ranges or {}).items():
            if key not in inputs or inputs[key] in (None, ""):
                continue
            raw = inputs[key]
            try:
                base = D(str(raw))
            except Exception:
                continue
            mode = (spec or {}).get("mode") or "factor"
            if mode == "absolute":
                lo = D(str(spec["min"]))
                hi = D(str(spec["max"]))
                u = rng.random()
                val = lo + (hi - lo) * D(str(u))
            else:
                lo = D(str(spec.get("low", "0.9")))
                hi = D(str(spec.get("high", "1.1")))
                u = rng.random()
                factor = lo + (hi - lo) * D(str(u))
                val = base * factor
            if isinstance(raw, int) and not isinstance(raw, bool):
                inputs[key] = int(val)
            else:
                inputs[key] = str(val)
        try:
            _, pr = run_pack_variant(pack, snapshot, inputs, variant=variant)
            m: MetricView = metrics_from_pack_run(pr)
        except Exception:
            skipped += 1
            continue
        if m.npv is not None:
            npvs.append(m.npv)
            if m.npv > 0:
                positive += 1
        if m.months_below_policy > 0 or m.max_shortfall_vs_policy > 0:
            breaches += 1

    npvs_sorted = sorted(npvs)
    n_ok = len(npvs_sorted)
    disclaimer = (
        "Bajo los rangos que has definido (no es una probabilidad de éxito del negocio). "
        "Cada simulación reutiliza el motor L0 del pack."
    )
    return {
        "n_sims": n,
        "n_completed": n_ok,
        "n_skipped": skipped,
        "seed": seed,
        "npv_p10": None if not npvs_sorted else str(_percentile(npvs_sorted, 0.10)),
        "npv_p50": None if not npvs_sorted else str(_percentile(npvs_sorted, 0.50)),
        "npv_p90": None if not npvs_sorted else str(_percentile(npvs_sorted, 0.90)),
        "prob_npv_positive": None if n_ok == 0 else round(positive / n_ok, 4),
        "prob_cash_breach": None if n_ok == 0 else round(breaches / max(n_ok, 1), 4),
        "disclaimer": disclaimer,
    }
