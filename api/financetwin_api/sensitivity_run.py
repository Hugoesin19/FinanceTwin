"""P6 — sensibilidad API (orquesta engine.analytics.sensitivity)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from financetwin_api.db import Store
from financetwin_api.packs_run import PACK_IDS, get_pack
from financetwin_engine import run_analysis, snapshot_from_dict


def run_sensitivity_for_company(
    store: Store,
    *,
    company_id: str,
    pack_id: str,
    inputs: dict[str, Any],
    variant: str = "base",
    include: list[str] | None = None,
) -> dict[str, Any]:
    if pack_id not in PACK_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown pack_id {pack_id!r}; have {list(PACK_IDS)}",
        )
    if store.get_company(company_id) is None:
        raise HTTPException(status_code=404, detail="company not found")
    cur = store.get_current_snapshot(company_id)
    if cur is None:
        raise HTTPException(status_code=400, detail="company has no current snapshot")
    model_version_id, snap_dict = cur

    try:
        snapshot = snapshot_from_dict(snap_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"stored snapshot invalid: {e}"
        ) from e

    pack = get_pack(pack_id)
    if not hasattr(pack, "analysis_plan"):
        raise HTTPException(
            status_code=400,
            detail=f"pack {pack_id!r} has no analysis_plan",
        )
    plan = pack.analysis_plan()
    if not (
        plan.get("sensitivity_vars")
        or plan.get("inverse_sensitivity")
        or plan.get("stress_tests")
    ):
        raise HTTPException(
            status_code=400,
            detail=f"pack {pack_id!r} has empty analysis_plan (P6 solo new_site MVP)",
        )

    blocks = tuple(include or ("direct", "inverse", "stress"))
    allowed = {"direct", "inverse", "stress"}
    bad = [b for b in blocks if b not in allowed]
    if bad:
        raise HTTPException(status_code=400, detail=f"unknown include blocks: {bad}")

    try:
        analysis = run_analysis(
            pack, snapshot, inputs, variant=variant, include=blocks
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Confirm MV not mutated
    cur_after = store.get_current_snapshot(company_id)
    if cur_after is None or cur_after[0] != model_version_id:
        raise HTTPException(
            status_code=500,
            detail="model version current was mutated unexpectedly",
        )

    return {
        "company_id": company_id,
        "model_version_id": model_version_id,
        **analysis,
    }
