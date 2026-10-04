"""Run Decision Packs via API — PLAN_PRODUCTO P1."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

from fastapi import HTTPException

from financetwin_api.db import Store
from financetwin_api.ops import variant_overrides
from financetwin_api.serialize import to_jsonable
from financetwin_engine import (
    AssetPurchasePack,
    FinancingPack,
    GenericInvestmentPack,
    HiringPack,
    LiquidityPlanPack,
    NewSitePack,
    calculate,
    snapshot_from_dict,
)
from financetwin_engine.mapper import ScenarioSpec, to_calculation_input
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot
from financetwin_engine.packs.base import BuiltScenarioBundle, Issue, has_errors
from financetwin_engine.version import ENGINE_VERSION

PACK_IDS = (
    "new_site",
    "financing",
    "asset_purchase",
    "hiring",
    "generic_investment",
    "liquidity_plan",
)


class DecisionPack(Protocol):
    id: str

    def resolve_defaults(
        self, snapshot: CompanyTwinSnapshot, user_partial: dict[str, Any]
    ) -> dict[str, Any]: ...

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]: ...

    def build(
        self, snapshot: CompanyTwinSnapshot, inputs: dict[str, Any]
    ) -> BuiltScenarioBundle: ...

    def actual_keys(self) -> list[str]: ...


def get_pack(pack_id: str) -> DecisionPack:
    registry: dict[str, type] = {
        "new_site": NewSitePack,
        "financing": FinancingPack,
        "asset_purchase": AssetPurchasePack,
        "hiring": HiringPack,
        "generic_investment": GenericInvestmentPack,
        "liquidity_plan": LiquidityPlanPack,
    }
    cls = registry.get(pack_id)
    if cls is None:
        raise KeyError(pack_id)
    pack = cls()
    if getattr(pack, "id", None) != pack_id:
        raise RuntimeError(f"pack class id mismatch: {pack_id!r} vs {getattr(pack, 'id', None)!r}")
    return pack


def _scenario_label(pack_id: str, resolved: dict[str, Any], variant: str) -> str:
    for key in (
        "site_name",
        "loan_name",
        "asset_name",
        "role_name",
        "name",
    ):
        if resolved.get(key):
            return f"{pack_id}:{resolved[key]}:{variant}"
    return f"{pack_id}:{variant}"


def run_pack_for_company(
    store: Store,
    *,
    company_id: str,
    pack_id: str,
    inputs: dict[str, Any],
    variant: str = "base",
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
    resolved = pack.resolve_defaults(snapshot, inputs)
    issues = pack.validate_inputs(resolved)
    if has_errors(issues):
        raise HTTPException(
            status_code=400,
            detail={
                "errors": [
                    {"code": i.code, "message": i.message}
                    for i in issues
                    if i.severity == "error"
                ]
            },
        )

    try:
        bundle = pack.build(snapshot, resolved)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if variant not in bundle.variants:
        raise HTTPException(
            status_code=400,
            detail=f"unknown variant {variant!r}; have {list(bundle.variants)}",
        )
    plan = bundle.variants[variant]
    overrides_json = variant_overrides(plan)
    auto_finance = bool(plan.auto_finance_deficits)

    scenario_id = store.create_scenario(
        company_id=company_id,
        name=_scenario_label(pack_id, resolved, variant),
        scenario_type=variant
        if variant in ("base", "conservative", "adverse")
        else "custom",
        base_model_version_id=model_version_id,
        anchor_year_month=plan.anchor_year_month,
        horizon_months=plan.horizon_months,
        discount_rate_annual=str(plan.discount_rate_annual),
        overrides=overrides_json,
        auto_finance_deficits=auto_finance,
    )

    rate = plan.discount_rate_annual
    if not isinstance(rate, Decimal):
        rate = Decimal(str(rate))

    mapped = to_calculation_input(
        snapshot,
        ScenarioSpec(
            anchor_year_month=plan.anchor_year_month,
            horizon_months=plan.horizon_months,
            discount_rate_annual=rate,
            auto_finance_deficits=auto_finance,
            overrides=plan.build_ops,
        ),
    )
    result = calculate(mapped.calculation_input)

    calc_in = to_jsonable(mapped.calculation_input)
    results = to_jsonable(result)
    run_id = store.create_calculation_run(
        scenario_id=scenario_id,
        company_id=company_id,
        engine_version=ENGINE_VERSION,
        model_version_id=model_version_id,
        inputs_hash=mapped.inputs_hash,
        calculation_input=calc_in,
        results=results,
        status="completed",
    )

    cur_after = store.get_current_snapshot(company_id)
    if cur_after is None or cur_after[0] != model_version_id:
        raise HTTPException(
            status_code=500,
            detail="model version current was mutated unexpectedly",
        )

    metrics = (
        to_jsonable(result.investment_metrics)
        if result.investment_metrics is not None
        else None
    )

    return {
        "company_id": company_id,
        "pack_id": pack_id,
        "model_version_id": model_version_id,
        "scenario_id": scenario_id,
        "calculation_run_id": run_id,
        "variant": variant,
        "engine_version": ENGINE_VERSION,
        "inputs_hash": mapped.inputs_hash,
        "result_hash": result.result_hash,
        "actual_keys": list(pack.actual_keys()),
        "investment_metrics": metrics,
        "financing_need": to_jsonable(result.financing_need),
        "policy_checks": to_jsonable(result.policy_checks),
        "warnings": list(result.warnings),
        "results": results,
    }
