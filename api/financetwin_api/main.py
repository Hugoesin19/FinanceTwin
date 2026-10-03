"""Finance Twin minimal API — F5/F6."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from financetwin_api.db import Store
from financetwin_api.ops import variant_overrides
from financetwin_api.serialize import to_jsonable
from financetwin_api.twin_loop import (
    preview_calibration,
    record_actuals,
    register_decision,
    transition_decision,
)
from financetwin_engine import NewSitePack, calculate, snapshot_from_dict
from financetwin_engine.mapper import ScenarioSpec, to_calculation_input
from financetwin_engine.packs.base import has_errors
from financetwin_engine.version import ENGINE_VERSION

DEFAULT_DB = os.environ.get(
    "FINANCETWIN_DB",
    str(Path(__file__).resolve().parents[1] / "data" / "financetwin.sqlite"),
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def get_store(request: Request) -> Store:
    return request.app.state.store


class CreateCompanyBody(BaseModel):
    name: str
    country: str = "ES"
    currency: str = "EUR"


class PutSnapshotBody(BaseModel):
    snapshot: dict[str, Any]
    label: str | None = None


class RunNewSiteBody(BaseModel):
    inputs: dict[str, Any]
    variant: str = Field(default="base", description="base | conservative | adverse")


class RegisterDecisionBody(BaseModel):
    title: str
    decision_pack_id: str
    decision_date: str
    calculation_run_id: str
    status: str = "approved"
    rationale: str = ""
    owner_user_id: str = "local"
    owner_label: str | None = None
    discarded_alternatives: list[Any] = Field(default_factory=list)
    accepted_risks: list[Any] = Field(default_factory=list)
    policy_exceptions: list[Any] = Field(default_factory=list)
    conditions: str | None = None
    calibrated_scenario_id: str | None = None


class TransitionDecisionBody(BaseModel):
    status: str


class ActualItem(BaseModel):
    variable_key: str
    forecast_value: str
    actual_value: str
    source: str | None = None
    notes: str | None = None


class RecordActualsBody(BaseModel):
    period_year_month: str
    items: list[ActualItem]
    source: str = "manual"
    recorded_by: str | None = None


class CalibrationPreviewBody(BaseModel):
    inputs: dict[str, Any]


def create_app(db_path: str | None = None) -> FastAPI:
    path = db_path or DEFAULT_DB

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = Store(path)
        yield

    application = FastAPI(
        title="Finance Twin API",
        version="0.1.0",
        description="Minimal local API (F5). No auth.",
        lifespan=lifespan,
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "engine_version": ENGINE_VERSION}

    @application.post("/companies")
    def create_company(body: CreateCompanyBody, request: Request) -> dict[str, Any]:
        store = get_store(request)
        row = store.create_company(body.name, body.country, body.currency)
        return {
            "id": row.id,
            "name": row.name,
            "country": row.country,
            "currency": row.currency,
            "created_at": row.created_at,
        }

    @application.put("/companies/{company_id}/snapshot")
    def put_snapshot(
        company_id: str,
        body: PutSnapshotBody,
        request: Request,
    ) -> dict[str, Any]:
        store = get_store(request)
        if store.get_company(company_id) is None:
            raise HTTPException(status_code=404, detail="company not found")
        try:
            snapshot_from_dict(body.snapshot)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"invalid snapshot: {e}") from e
        mv_id = store.put_current_snapshot(
            company_id, body.snapshot, label=body.label
        )
        return {
            "company_id": company_id,
            "model_version_id": mv_id,
            "is_current": True,
        }

    @application.get("/companies/{company_id}/snapshot")
    def get_snapshot(company_id: str, request: Request) -> dict[str, Any]:
        store = get_store(request)
        if store.get_company(company_id) is None:
            raise HTTPException(status_code=404, detail="company not found")
        cur = store.get_current_snapshot(company_id)
        if cur is None:
            raise HTTPException(status_code=404, detail="no current snapshot")
        mv_id, snap = cur
        return {"model_version_id": mv_id, "snapshot": snap}

    @application.post("/companies/{company_id}/packs/new_site/run")
    def run_new_site(
        company_id: str,
        body: RunNewSiteBody,
        request: Request,
    ) -> dict[str, Any]:
        store = get_store(request)
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

        pack = NewSitePack()
        resolved = pack.resolve_defaults(snapshot, body.inputs)
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

        if body.variant not in bundle.variants:
            raise HTTPException(
                status_code=400,
                detail=f"unknown variant {body.variant!r}; have {list(bundle.variants)}",
            )
        plan = bundle.variants[body.variant]
        # Persist JSON-safe overrides; calculate with live BuildOps (no round-trip).
        overrides_json = variant_overrides(plan)

        scenario_id = store.create_scenario(
            company_id=company_id,
            name=f"new_site:{resolved.get('site_name', 'site')}:{body.variant}",
            scenario_type=body.variant
            if body.variant in ("base", "conservative", "adverse")
            else "custom",
            base_model_version_id=model_version_id,
            anchor_year_month=plan.anchor_year_month,
            horizon_months=plan.horizon_months,
            discount_rate_annual=str(plan.discount_rate_annual),
            overrides=overrides_json,
            auto_finance_deficits=False,
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
                auto_finance_deficits=False,
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
            "model_version_id": model_version_id,
            "scenario_id": scenario_id,
            "calculation_run_id": run_id,
            "variant": body.variant,
            "engine_version": ENGINE_VERSION,
            "inputs_hash": mapped.inputs_hash,
            "result_hash": result.result_hash,
            "investment_metrics": metrics,
            "financing_need": to_jsonable(result.financing_need),
            "policy_checks": to_jsonable(result.policy_checks),
            "warnings": list(result.warnings),
            "results": results,
        }

    @application.get("/calculation-runs/{run_id}")
    def get_run(run_id: str, request: Request) -> dict[str, Any]:
        store = get_store(request)
        row = store.get_calculation_run(run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="calculation_run not found")
        return row

    # --- F7 Twin Loop ---

    @application.post("/companies/{company_id}/decisions")
    def create_decision(
        company_id: str, body: RegisterDecisionBody, request: Request
    ) -> dict[str, Any]:
        store = get_store(request)
        try:
            return register_decision(
                store,
                company_id=company_id,
                title=body.title,
                decision_pack_id=body.decision_pack_id,
                decision_date=body.decision_date,
                status=body.status,
                calculation_run_id=body.calculation_run_id,
                rationale=body.rationale,
                owner_user_id=body.owner_user_id,
                owner_label=body.owner_label,
                discarded_alternatives=body.discarded_alternatives,
                accepted_risks=body.accepted_risks,
                policy_exceptions=body.policy_exceptions,
                conditions=body.conditions,
                calibrated_scenario_id=body.calibrated_scenario_id,
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @application.get("/decisions/{decision_id}")
    def get_decision(decision_id: str, request: Request) -> dict[str, Any]:
        store = get_store(request)
        row = store.get_decision(decision_id)
        if row is None:
            raise HTTPException(status_code=404, detail="decision not found")
        return row

    @application.post("/decisions/{decision_id}/status")
    def post_decision_status(
        decision_id: str, body: TransitionDecisionBody, request: Request
    ) -> dict[str, Any]:
        store = get_store(request)
        try:
            return transition_decision(store, decision_id, body.status)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @application.post("/decisions/{decision_id}/actuals")
    def post_actuals(
        decision_id: str, body: RecordActualsBody, request: Request
    ) -> dict[str, Any]:
        store = get_store(request)
        try:
            return record_actuals(
                store,
                decision_id=decision_id,
                period_year_month=body.period_year_month,
                items=[i.model_dump() for i in body.items],
                source=body.source,
                recorded_by=body.recorded_by,
            )
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @application.get("/companies/{company_id}/packs/{pack_id}/bias-profiles")
    def get_bias_profiles(
        company_id: str, pack_id: str, request: Request
    ) -> dict[str, Any]:
        store = get_store(request)
        if store.get_company(company_id) is None:
            raise HTTPException(status_code=404, detail="company not found")
        return {
            "company_id": company_id,
            "decision_pack_id": pack_id,
            "profiles": store.list_bias_profiles(company_id, pack_id),
        }

    @application.post("/companies/{company_id}/packs/{pack_id}/calibration/preview")
    def post_calibration_preview(
        company_id: str,
        pack_id: str,
        body: CalibrationPreviewBody,
        request: Request,
    ) -> dict[str, Any]:
        store = get_store(request)
        if store.get_company(company_id) is None:
            raise HTTPException(status_code=404, detail="company not found")
        try:
            return preview_calibration(
                store,
                company_id=company_id,
                decision_pack_id=pack_id,
                inputs=body.inputs,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # F6 — UI mínima (same-origin; sin Node)
    if STATIC_DIR.is_dir():
        application.mount(
            "/static", StaticFiles(directory=str(STATIC_DIR)), name="static"
        )

        @application.get("/")
        def ui_index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return application


app = create_app()
