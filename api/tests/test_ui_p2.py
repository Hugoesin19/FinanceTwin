"""P2 — UI Decision Studio: 6 packs + API genérica."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from financetwin_api.packs_run import PACK_IDS

CANONICAL = list(PACK_IDS)

# Twin UI con streams (app.js twinSnapshot) — camino feliz liquidity + resto.
UI_TWIN_WITH_STREAMS = {
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
    "revenue_streams": [
        {
            "id": "R0",
            "name": "base",
            "revenue_type": "recurring",
            "start_year_month": "2027-01",
            "base_monthly_revenue": "30000",
            "gross_margin_pct": "0.4",
            "collection_days": 0,
        }
    ],
    "cost_items": [
        {
            "id": "C0",
            "name": "opex",
            "nature": "fixed",
            "start_year_month": "2027-01",
            "amount_monthly": "5000",
            "payment_days": 0,
        }
    ],
}

# Defaults alineados con PACK_FORMS en app.js
UI_PACK_INPUTS = {
    "new_site": {
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
    },
    "financing": {
        "loan_name": "Puente",
        "principal": "50000",
        "disbursement_year_month": "2027-01",
        "annual_rate": "0.06",
        "term_months": 24,
        "use_of_funds": "cash_buffer",
        "horizon_months": 24,
    },
    "asset_purchase": {
        "asset_name": "Furgoneta",
        "acquisition_cost": "25000",
        "acquisition_year_month": "2027-01",
        "useful_life_months": 60,
        "funding_mode": "cash",
        "opex_savings_monthly": "400",
        "horizon_months": 24,
        "discount_rate_annual": "0.08",
    },
    "hiring": {
        "role_name": "Comercial",
        "headcount": 2,
        "employer_cost_per_person": "3000",
        "start_year_month": "2027-01",
        "expected_monthly_revenue_uplift": "8000",
        "gross_margin_pct": "0.4",
        "horizon_months": 12,
        "discount_rate_annual": "0.08",
    },
    "generic_investment": {
        "name": "Software",
        "capex_schedule": [{"year_month": "2027-01", "amount": "20000"}],
        "horizon_months": 24,
        "benefit_cadence": "monthly",
        "benefit_amount": "1500",
        "benefit_type": "revenue",
        "gross_margin_pct": "0.8",
        "debt_amount": "0",
        "equity_amount": "20000",
        "discount_rate_annual": "0.08",
    },
    "liquidity_plan": {
        "horizon_months": 12,
        "anchor_year_month": "2027-01",
        "sales_adjustment_pct": "-0.10",
        "extra_monthly_opex": "1000",
        "one_off_outflows": [
            {"year_month": "2027-03", "amount": "5000", "label": "tax"}
        ],
    },
}


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "ui_p2.sqlite"))
    with TestClient(application) as c:
        yield c


def test_ui_references_all_canonical_packs(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    for pack in CANONICAL:
        assert f'value="{pack}"' in html
        assert f"{pack}:" in js or f'"{pack}"' in js
    assert "PACK_FORMS" in js
    assert "/packs/${packId}/run" in js
    # no endpoint inventado
    assert "/packs/new_site/run" not in js or "${packId}" in js


@pytest.mark.parametrize("pack_id", CANONICAL)
def test_ui_defaults_run_each_pack(client: TestClient, pack_id: str) -> None:
    company_id = client.post("/companies", json={"name": f"UI-{pack_id}"}).json()["id"]
    put = client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS, "label": "ui"},
    )
    assert put.status_code == 200
    mv = put.json()["model_version_id"]
    r = client.post(
        f"/companies/{company_id}/packs/{pack_id}/run",
        json={"inputs": UI_PACK_INPUTS[pack_id], "variant": "base"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pack_id"] == pack_id
    assert body["model_version_id"] == mv
    assert body["financing_need"] is not None
    assert isinstance(body["financing_need"]["min_cash"], str)
    assert client.get(f"/companies/{company_id}/snapshot").json()["model_version_id"] == mv
