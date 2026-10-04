"""P3 — Informe usable + comparación de variantes (campos ⊆ API)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from tests.test_ui_p2 import UI_PACK_INPUTS, UI_TWIN_WITH_STREAMS

# Checklist documentado: campos que la UI P3 pinta (debe ⊆ respuesta API).
UI_REPORT_FIELDS = {
    "investment_metrics": {
        "npv",
        "irr_annual",
        "payback_simple",
        "payback_discounted",
        "warnings",
    },
    "financing_need": {
        "min_cash",
        "min_cash_month",
        "max_shortfall_vs_policy",
        "first_shortfall_month",
        "months_below_policy",
    },
    "policy_checks": {"policy_id", "status", "value", "threshold", "message"},
    "cash_flow": {
        "t",
        "opening_cash",
        "closing_cash",
        "operating_cash_flow",
        "capex_paid",
        "loan_drawdowns",
        "net_cash_flow",
    },
    "meta": {
        "pack_id",
        "calculation_run_id",
        "scenario_id",
        "model_version_id",
        "engine_version",
        "variant",
        "inputs_hash",
        "result_hash",
        "warnings",
    },
}


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "ui_p3.sqlite"))
    with TestClient(application) as c:
        yield c


def test_ui_p3_markup_has_compare_and_exec_report(client: TestClient) -> None:
    html = client.get("/").text
    assert 'id="btn-compare"' in html
    assert 'id="compare"' in html
    assert "Informe ejecutivo" in html or "Resultado" in html
    assert "operating_cash_flow" in html
    assert 'id="policy-summary"' in html
    assert 'id="trace"' in html


def test_ui_p3_js_compares_three_api_calls_no_homemade_math(client: TestClient) -> None:
    js = client.get("/static/app.js").text
    assert "compareVariants" in js
    assert "REPORT_FIELDS" in js
    assert '["base", "conservative", "adverse"]' in js or "VARIANTS" in js
    assert "postPackRun" in js
    # tres variantes vía API; sin agregaciones caseras de métricas
    assert "average(" not in js.lower()
    assert "Math." not in js
    assert "funding_gap" not in js
    assert "payback_months" not in js
    for field in (
        "npv",
        "irr_annual",
        "payback_simple",
        "min_cash",
        "max_shortfall_vs_policy",
        "operating_cash_flow",
    ):
        assert field in js


def test_ui_report_fields_subset_of_api_response(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "P3"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS},
    )
    runs = {}
    for variant in ("base", "conservative", "adverse"):
        r = client.post(
            f"/companies/{company_id}/packs/new_site/run",
            json={"inputs": UI_PACK_INPUTS["new_site"], "variant": variant},
        )
        assert r.status_code == 200, r.text
        runs[variant] = r.json()

    body = runs["base"]
    im = body.get("investment_metrics") or {}
    fn = body["financing_need"]
    # campos UI ⊆ API (warnings de métricas puede ser lista vacía serializada)
    assert (
        UI_REPORT_FIELDS["investment_metrics"] - {"warnings"}
    ) <= set(im.keys())
    if "warnings" in im:
        assert "warnings" in UI_REPORT_FIELDS["investment_metrics"]
    assert UI_REPORT_FIELDS["financing_need"] <= set(fn.keys())
    assert UI_REPORT_FIELDS["meta"] - {"warnings"} <= set(body.keys())
    assert body["policy_checks"]
    assert UI_REPORT_FIELDS["policy_checks"] <= set(body["policy_checks"][0].keys())
    cf0 = body["results"]["cash_flow"][0]
    assert UI_REPORT_FIELDS["cash_flow"] <= set(cf0.keys())

    # comparación: tres respuestas distintas del motor (no un solo run)
    assert runs["base"]["calculation_run_id"] != runs["adverse"]["calculation_run_id"]
    assert runs["base"]["result_hash"] != runs["adverse"]["result_hash"]
    assert isinstance(runs["base"]["investment_metrics"]["npv"], str)
    assert isinstance(runs["adverse"]["investment_metrics"]["npv"], str)


def test_ui_js_report_fields_match_checklist(client: TestClient) -> None:
    js = client.get("/static/app.js").text
    for group, fields in UI_REPORT_FIELDS.items():
        assert group in js or group == "meta"
        for field in fields:
            assert field in js, field
