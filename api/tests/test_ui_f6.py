"""F6 — UI mínima smoke (served by API)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app

# Defaults del formulario HTML (camino feliz documentado).
UI_DEFAULT_SNAPSHOT = {
    "schema_version": "1.0",
    "company": {
        "currency": "EUR",
        "opening_cash": "80000",
        "default_purchase_payment_days": 0,
    },
    "fiscal": {
        "vat_rate": "0",
        "vat_settlement": "monthly",
        "vat_payment_lag_months": 0,
        "corp_tax_rate": "0",
        "corp_tax_payment_mode": "none",
    },
    "policies": {"min_cash": "0"},
}

UI_DEFAULT_INPUTS = {
    "site_name": "Tienda Alicante",
    "open_year_month": "2027-01",
    "capex_total": "350000",
    "sales_run_rate": "40000",
    "gross_margin_pct": "0.40",
    "rent_monthly": "4500",
    "other_opex_monthly": "1500",
    "headcount": 2,
    "employer_cost_per_person": "2800",
    "debt_amount": "200000",
    "equity_amount": "150000",
    "loan_term_months": 60,
    "loan_annual_rate": "0.055",
    "horizon_months": 24,
    "discount_rate_annual": "0.08",
    "collection_days": 0,
}


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "ui.sqlite"))
    with TestClient(application) as c:
        yield c


def test_ui_index_served(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Decision Studio" in r.text
    assert "/static/app.js" in r.text
    # Defaults twin + selector de packs (P2)
    assert 'id="opening_cash" value="80000"' in r.text
    assert 'id="pack_id"' in r.text
    assert 'id="pack_fields"' in r.text
    for pack in (
        "new_site",
        "financing",
        "asset_purchase",
        "hiring",
        "generic_investment",
        "liquidity_plan",
    ):
        assert f'value="{pack}"' in r.text


def test_ui_static_assets_use_engine_field_names(client: TestClient) -> None:
    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert "irr_annual" in js.text
    assert "payback_simple" in js.text
    assert "max_shortfall_vs_policy" in js.text
    assert "first_shortfall_month" in js.text
    assert "hydrateTwin" in js.text
    assert "restoreSession" in js.text
    # P2: API genérica, no hardcode solo new_site
    assert "/packs/${packId}/run" in js.text or "/packs/${" in js.text
    assert "PACK_FORMS" in js.text
    assert "Tienda Alicante" in js.text
    assert "350000" in js.text
    # No inventar aliases
    assert "funding_gap" not in js.text
    assert "payback_months" not in js.text
    assert "row.year_month" not in js.text
    assert "below_min_cash" not in js.text

    css = client.get("/static/styles.css")
    assert css.status_code == 200


def test_ui_happy_path_golden_npv(client: TestClient) -> None:
    """Defaults UI → VAN fijado; prueba DoD «números del motor»."""
    company_id = client.post("/companies", json={"name": "UI Co"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": UI_DEFAULT_SNAPSHOT},
    )
    run = client.post(
        f"/companies/{company_id}/packs/new_site/run",
        json={"inputs": UI_DEFAULT_INPUTS, "variant": "base"},
    )
    assert run.status_code == 200, run.text
    body = run.json()
    im = body["investment_metrics"]
    fn = body["financing_need"]
    assert im["npv"] == "-361172.48"
    assert im["irr_annual"] is not None
    assert im["payback_simple"] is None
    assert im["payback_discounted"] is None
    assert fn["min_cash"] == "-25042.76"
    assert fn["min_cash_month"] == 11
    assert fn["max_shortfall_vs_policy"] == "25042.76"
    cf0 = body["results"]["cash_flow"][0]
    assert cf0["capex_paid"] == "350000.00"
    assert cf0["loan_drawdowns"] == "200000.00"
    assert cf0["opening_cash"] == "80000.00"
    assert any(
        p["policy_id"] == "min_cash" and p["status"] == "fail"
        for p in body["policy_checks"]
    )


def test_get_snapshot_distinguishes_missing_company(client: TestClient) -> None:
    r = client.get("/companies/00000000-0000-0000-0000-000000000000/snapshot")
    assert r.status_code == 404
    assert r.json()["detail"] == "company not found"

    company_id = client.post("/companies", json={"name": "Empty"}).json()["id"]
    r2 = client.get(f"/companies/{company_id}/snapshot")
    assert r2.status_code == 404
    assert r2.json()["detail"] == "no current snapshot"


def test_funding_error_clears_path_for_ui(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "X"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": UI_DEFAULT_SNAPSHOT},
    )
    bad = dict(UI_DEFAULT_INPUTS)
    bad["equity_amount"] = "1000"
    r = client.post(
        f"/companies/{company_id}/packs/new_site/run",
        json={"inputs": bad, "variant": "base"},
    )
    assert r.status_code == 400
