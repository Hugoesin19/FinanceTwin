"""API orchestration for tornado / Monte Carlo / scorecard / DSCR."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from financetwin_api.db import Store
from financetwin_api.packs_run import get_pack
from financetwin_api.serialize import to_jsonable
from financetwin_engine import snapshot_from_dict
from financetwin_engine.analytics.montecarlo import run_montecarlo
from financetwin_engine.analytics.scorecard import build_scorecard
from financetwin_engine.analytics.tornado import run_tornado
from financetwin_engine.calc.decimal_money import D


def _load_pack_snapshot(store: Store, company_id: str, pack_id: str):
    if store.get_company(company_id) is None:
        raise HTTPException(status_code=404, detail="company not found")
    cur = store.get_current_snapshot(company_id)
    if cur is None:
        raise HTTPException(status_code=400, detail="company has no current snapshot")
    _, snap_dict = cur
    try:
        snapshot = snapshot_from_dict(snap_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"stored snapshot invalid: {e}") from e
    try:
        pack = get_pack(pack_id)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"unknown pack_id {pack_id!r}") from e
    return pack, snapshot


def run_tornado_for_company(
    store: Store,
    *,
    company_id: str,
    pack_id: str,
    inputs: dict[str, Any],
    variant: str = "base",
    metric: str = "npv",
) -> dict[str, Any]:
    pack, snapshot = _load_pack_snapshot(store, company_id, pack_id)
    if not hasattr(pack, "analysis_plan"):
        raise HTTPException(status_code=400, detail="pack has no analysis_plan")
    try:
        result = run_tornado(pack, snapshot, inputs, variant=variant, metric=metric)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"company_id": company_id, "pack_id": pack_id, **result}


def run_montecarlo_for_company(
    store: Store,
    *,
    company_id: str,
    pack_id: str,
    inputs: dict[str, Any],
    variant: str = "base",
    ranges: dict[str, dict[str, str]] | None = None,
    n_sims: int = 100,
    seed: int = 42,
) -> dict[str, Any]:
    pack, snapshot = _load_pack_snapshot(store, company_id, pack_id)
    n = min(max(1, int(n_sims)), 500)
    try:
        result = run_montecarlo(
            pack=pack,
            snapshot=snapshot,
            base_inputs=inputs,
            variant=variant,
            ranges=ranges
            or {
                "sales_run_rate": {"low": "0.85", "high": "1.15"},
                "gross_margin_pct": {"low": "0.90", "high": "1.05"},
                "capex_total": {"low": "0.95", "high": "1.15"},
            },
            n_sims=n,
            seed=seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"company_id": company_id, "pack_id": pack_id, "variant": variant, **result}


def scorecard_from_run_payload(
    run: dict[str, Any],
    montecarlo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_scorecard(
        investment_metrics=run.get("investment_metrics"),
        financing_need=run.get("financing_need"),
        policy_checks=run.get("policy_checks"),
        montecarlo=montecarlo,
    )


def dscr_from_results(results: dict[str, Any] | None) -> dict[str, Any]:
    """DSCR = EBITDA / (principal + interest) per period from engine series."""
    if not results:
        return {"available": False, "rows": [], "min_dscr": None}
    pnl = results.get("pnl") or []
    cash = results.get("cash_flow") or []
    rows: list[dict[str, Any]] = []
    n = min(len(pnl), len(cash))
    for i in range(n):
        try:
            ebitda = D(str(pnl[i].get("ebitda")))
            principal = D(str(cash[i].get("loan_principal_repaid") or "0"))
            interest = D(str(cash[i].get("loan_interest_paid") or "0"))
        except Exception:
            continue
        service = principal + interest
        if service <= 0:
            continue
        dscr = ebitda / service
        rows.append(
            {
                "t": cash[i].get("t"),
                "ebitda": str(ebitda),
                "debt_service": str(service),
                "dscr": str(dscr),
            }
        )
    if not rows:
        return {"available": False, "rows": [], "min_dscr": None}
    min_row = min(rows, key=lambda r: D(r["dscr"]))
    return {
        "available": True,
        "rows": to_jsonable(rows),
        "min_dscr": min_row["dscr"],
        "min_dscr_t": min_row["t"],
    }
