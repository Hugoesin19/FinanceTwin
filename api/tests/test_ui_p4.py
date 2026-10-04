"""P4 — Twin Loop UI + GET list decisions."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from tests.test_ui_p2 import UI_PACK_INPUTS, UI_TWIN_WITH_STREAMS


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p4.sqlite"))
    with TestClient(application) as c:
        yield c


def test_list_decisions_empty_and_after_register(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "P4"}).json()["id"]
    empty = client.get(f"/companies/{company_id}/decisions")
    assert empty.status_code == 200
    assert empty.json()["decisions"] == []

    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS},
    )
    run = client.post(
        f"/companies/{company_id}/packs/new_site/run",
        json={"inputs": UI_PACK_INPUTS["new_site"], "variant": "base"},
    )
    assert run.status_code == 200
    run_id = run.json()["calculation_run_id"]

    dec = client.post(
        f"/companies/{company_id}/decisions",
        json={
            "title": "Abrir tienda",
            "decision_pack_id": "new_site",
            "decision_date": "2027-01-15",
            "calculation_run_id": run_id,
            "status": "executed",
            "rationale": "ok",
        },
    )
    assert dec.status_code == 200, dec.text
    listed = client.get(f"/companies/{company_id}/decisions")
    assert listed.status_code == 200
    rows = listed.json()["decisions"]
    assert len(rows) == 1
    assert rows[0]["id"] == dec.json()["id"]
    assert rows[0]["status"] == "executed"
    assert rows[0]["actual_results_count"] == 0
    assert "frozen_projection" not in rows[0]

    # after actuals, list count increments
    rec = client.post(
        f"/decisions/{dec.json()['id']}/actuals",
        json={
            "period_year_month": "2027-06",
            "items": [
                {
                    "variable_key": "sales_monthly",
                    "forecast_value": "40000",
                    "actual_value": "36000",
                }
            ],
        },
    )
    assert rec.status_code == 200, rec.text
    listed2 = client.get(f"/companies/{company_id}/decisions").json()["decisions"]
    assert listed2[0]["actual_results_count"] == 1

    preview = client.post(
        f"/companies/{company_id}/packs/new_site/calibration/preview",
        json={"inputs": UI_PACK_INPUTS["new_site"]},
    ).json()
    assert preview["offered"] is False


def test_list_decisions_404_unknown_company(client: TestClient) -> None:
    r = client.get("/companies/00000000-0000-0000-0000-000000000000/decisions")
    assert r.status_code == 404


def test_ui_p4_smoke_twin_loop_markup_and_api_paths(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert 'id="sec-twin-loop"' in html
    assert 'id="btn-register-decision"' in html
    assert 'id="btn-record-actuals"' in html
    assert 'id="btn-load-bias"' in html
    assert 'id="btn-calib-preview"' in html
    assert 'id="btn-apply-calib"' in html
    assert "offered=true" in html or "offered" in html

    assert "registerDecision" in js
    assert "recordActuals" in js
    assert "previewCalibration" in js
    assert "/decisions" in js
    assert "bias-profiles" in js
    assert "calibration/preview" in js
    assert 'offered === true' in js or 'offered===true' in js
    assert "Math." not in js
    assert "calibrated_inputs" in js


def test_ui_p4_calibration_gate_visible_in_js(client: TestClient) -> None:
    js = client.get("/static/app.js").text
    # no ofrecer apply sin offered
    assert "btn-apply-calib" in js
    assert "offered" in js
    assert "n≥3" in js or "n>=3" in js or "n_observations" in js
