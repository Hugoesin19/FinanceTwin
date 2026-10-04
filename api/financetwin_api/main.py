"""Finance Twin API — F5–F7 + P1 packs + P5 CSV import."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from financetwin_api.csv_import import (
    TwinCsvError,
    format_import_error,
    parse_and_validate_twin_csv,
)
from financetwin_api.db import Store
from financetwin_api.packs_run import PACK_IDS, run_pack_for_company
from financetwin_api.report_html import render_executive_html
from financetwin_api.serialize import to_jsonable
from financetwin_api.sensitivity_run import run_sensitivity_for_company
from financetwin_api.twin_loop import (
    preview_calibration,
    record_actuals,
    register_decision,
    transition_decision,
)
from financetwin_api.twin_quality import assess_twin_quality
from financetwin_engine import snapshot_from_dict
from financetwin_engine.mapper.snapshot import SnapshotValidationError
from financetwin_engine.version import ENGINE_VERSION

DEFAULT_DB = os.environ.get(
    "FINANCETWIN_DB",
    str(Path(__file__).resolve().parents[1] / "data" / "financetwin.sqlite"),
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"


def get_store(request: Request) -> Store:
    return request.app.state.store


class CreateCompanyBody(BaseModel):
    name: str
    country: str = "ES"
    currency: str = "EUR"


class PutSnapshotBody(BaseModel):
    snapshot: dict[str, Any]
    label: str | None = None


class RunPackBody(BaseModel):
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


class SensitivityBody(BaseModel):
    inputs: dict[str, Any]
    variant: str = Field(default="base")
    include: list[str] = Field(
        default_factory=lambda: ["direct", "inverse", "stress"],
        description="direct | inverse | stress",
    )


class ExecutiveReportBody(BaseModel):
    run: dict[str, Any]
    compare: dict[str, Any] | None = None
    company_name: str = "Empresa"


def create_app(db_path: str | None = None) -> FastAPI:
    path = db_path or DEFAULT_DB

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = Store(path)
        yield

    application = FastAPI(
        title="Finance Twin API",
        version="0.1.0",
        description="Finance Twin API (F5–F7 + P1–P13 uso C). No auth.",
        lifespan=lifespan,
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "engine_version": ENGINE_VERSION}

    @application.get("/companies")
    def list_companies(request: Request) -> dict[str, Any]:
        store = get_store(request)
        rows = store.list_companies()
        return {
            "companies": [
                {
                    "id": r.id,
                    "name": r.name,
                    "country": r.country,
                    "currency": r.currency,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
        }

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
        return {
            "model_version_id": mv_id,
            "snapshot": snap,
            "quality": assess_twin_quality(snap),
        }

    @application.get("/companies/{company_id}/twin-quality")
    def twin_quality(company_id: str, request: Request) -> dict[str, Any]:
        store = get_store(request)
        if store.get_company(company_id) is None:
            raise HTTPException(status_code=404, detail="company not found")
        cur = store.get_current_snapshot(company_id)
        if cur is None:
            raise HTTPException(status_code=404, detail="no current snapshot")
        mv_id, snap = cur
        return {
            "company_id": company_id,
            "model_version_id": mv_id,
            "quality": assess_twin_quality(snap),
        }

    @application.get("/templates/twin_snapshot_template.csv")
    def download_twin_template() -> FileResponse:
        path = TEMPLATES_DIR / "twin_snapshot_template.csv"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="template not found")
        return FileResponse(
            path,
            media_type="text/csv",
            filename="twin_snapshot_template.csv",
        )

    @application.post("/companies/{company_id}/imports/twin-csv")
    async def import_twin_csv(
        company_id: str,
        request: Request,
        file: UploadFile = File(...),
        label: str | None = Form(default=None),
    ) -> dict[str, Any]:
        """P5 — CSV plantilla → validate → nueva ModelVersion current."""
        store = get_store(request)
        if store.get_company(company_id) is None:
            raise HTTPException(status_code=404, detail="company not found")
        raw_bytes = await file.read()
        try:
            text = raw_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail={"code": "csv_encoding", "message": "CSV must be UTF-8"},
            ) from e
        try:
            snapshot = parse_and_validate_twin_csv(text)
        except (TwinCsvError, SnapshotValidationError, ValueError, TypeError, KeyError) as e:
            raise HTTPException(status_code=400, detail=format_import_error(e)) from e

        mv_id = store.put_current_snapshot(
            company_id,
            snapshot,
            label=label or (file.filename and f"csv:{file.filename}") or "csv-import",
        )
        return {
            "company_id": company_id,
            "model_version_id": mv_id,
            "is_current": True,
            "source_filename": file.filename,
            "snapshot": snapshot,
            "quality": assess_twin_quality(snapshot),
        }

    @application.get("/packs")
    def list_packs() -> dict[str, Any]:
        return {"packs": list(PACK_IDS)}

    @application.post("/companies/{company_id}/reports/executive")
    def executive_report(
        company_id: str, body: ExecutiveReportBody, request: Request
    ) -> HTMLResponse:
        """P10 — HTML descargable; solo pinta el run/compare enviados (sin recalcular)."""
        store = get_store(request)
        company = store.get_company(company_id)
        if company is None:
            raise HTTPException(status_code=404, detail="company not found")
        if not isinstance(body.run, dict) or not body.run.get("calculation_run_id"):
            raise HTTPException(
                status_code=400, detail="run.calculation_run_id required"
            )
        name = body.company_name or company.name
        html_doc = render_executive_html(
            company_name=name, run=body.run, compare=body.compare
        )
        headers = {
            "Content-Disposition": 'attachment; filename="informe_finance_twin.html"'
        }
        return HTMLResponse(content=html_doc, media_type="text/html; charset=utf-8", headers=headers)

    @application.post("/companies/{company_id}/packs/{pack_id}/run")
    def run_pack(
        company_id: str,
        pack_id: str,
        body: RunPackBody,
        request: Request,
    ) -> dict[str, Any]:
        """Ejecuta cualquier pack MVP (incl. new_site). Persiste Scenario + CalculationRun."""
        store = get_store(request)
        return run_pack_for_company(
            store,
            company_id=company_id,
            pack_id=pack_id,
            inputs=body.inputs,
            variant=body.variant,
        )

    @application.post("/companies/{company_id}/packs/{pack_id}/sensitivity")
    def run_sensitivity(
        company_id: str,
        pack_id: str,
        body: SensitivityBody,
        request: Request,
    ) -> dict[str, Any]:
        """P6 — sensibilidad/inversa/stress (re-llama al motor; no muta MV)."""
        store = get_store(request)
        return run_sensitivity_for_company(
            store,
            company_id=company_id,
            pack_id=pack_id,
            inputs=body.inputs,
            variant=body.variant,
            include=body.include,
        )

    @application.get("/calculation-runs/{run_id}")
    def get_run(run_id: str, request: Request) -> dict[str, Any]:
        store = get_store(request)
        row = store.get_calculation_run(run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="calculation_run not found")
        return row

    # --- F7 Twin Loop ---

    @application.get("/companies/{company_id}/decisions")
    def list_company_decisions(company_id: str, request: Request) -> dict[str, Any]:
        store = get_store(request)
        if store.get_company(company_id) is None:
            raise HTTPException(status_code=404, detail="company not found")
        return {"company_id": company_id, "decisions": store.list_decisions(company_id)}

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
