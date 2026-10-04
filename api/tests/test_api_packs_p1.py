"""P1 — API genérica: los 6 packs MVP."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from financetwin_api.packs_run import PACK_IDS


@pytest.fixture()
def client(tmp_path: Path):
    db = tmp_path / "p1.sqlite"
    application = create_app(str(db))
    with TestClient(application) as c:
        yield c


def _base_twin():
    """Twin con streams — necesario para liquidity_plan / ajustes."""
    return {
        "schema_version": "1.0",
        "company": {
            "currency": "EUR",
            "opening_cash": "150000",
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


def _find_floats(obj, path=""):
    bad = []
    if isinstance(obj, float):
        bad.append(path)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            bad.extend(_find_floats(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad.extend(_find_floats(v, f"{path}[{i}]"))
    return bad


def _pack_cases() -> list[tuple[str, dict]]:
    return [
        (
            "new_site",
            {
                "site_name": "Tienda P1",
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
        ),
        (
            "financing",
            {
                "loan_name": "Puente",
                "principal": "50000",
                "disbursement_year_month": "2027-01",
                "annual_rate": "0.06",
                "term_months": 24,
                "use_of_funds": "cash_buffer",
                "horizon_months": 24,
            },
        ),
        (
            "asset_purchase",
            {
                "asset_name": "Furgoneta",
                "acquisition_cost": "25000",
                "acquisition_year_month": "2027-01",
                "useful_life_months": 60,
                "funding_mode": "cash",
                "opex_savings_monthly": "400",
                "horizon_months": 24,
                "discount_rate_annual": "0.08",
            },
        ),
        (
            "hiring",
            {
                "role_name": "Comercial",
                "headcount": 2,
                "employer_cost_per_person": "3000",
                "start_year_month": "2027-01",
                "expected_monthly_revenue_uplift": "8000",
                "gross_margin_pct": "0.4",
                "horizon_months": 12,
                "discount_rate_annual": "0.08",
            },
        ),
        (
            "generic_investment",
            {
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
        ),
        (
            "liquidity_plan",
            {
                "horizon_months": 12,
                "anchor_year_month": "2027-01",
                "sales_adjustment_pct": "-0.10",
                "extra_monthly_opex": "1000",
                "one_off_outflows": [
                    {"year_month": "2027-03", "amount": "5000", "label": "tax"}
                ],
            },
        ),
    ]


def test_list_packs(client: TestClient) -> None:
    r = client.get("/packs")
    assert r.status_code == 200
    assert r.json()["packs"] == list(PACK_IDS)
    assert set(r.json()["packs"]) == {
        "new_site",
        "financing",
        "asset_purchase",
        "hiring",
        "generic_investment",
        "liquidity_plan",
    }


def test_unknown_pack_400(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "X"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": _base_twin()},
    )
    r = client.post(
        f"/companies/{company_id}/packs/not_a_pack/run",
        json={"inputs": {}, "variant": "base"},
    )
    assert r.status_code == 400


def test_pack_validation_errors_400(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Bad"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": _base_twin()},
    )
    r = client.post(
        f"/companies/{company_id}/packs/financing/run",
        json={
            "inputs": {
                "loan_name": "X",
                "principal": "10000",
                "disbursement_year_month": "2027-01",
                "annual_rate": "0.05",
                "term_months": 12,
                "grace_months": 3,
                "use_of_funds": "general",
            },
            "variant": "base",
        },
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["errors"]
    assert "code" in detail["errors"][0]


@pytest.mark.parametrize("pack_id,inputs", _pack_cases())
def test_each_pack_runs_and_does_not_mutate_mv(
    client: TestClient, pack_id: str, inputs: dict
) -> None:
    company_id = client.post("/companies", json={"name": f"Co-{pack_id}"}).json()["id"]
    put = client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": _base_twin(), "label": "v1"},
    )
    assert put.status_code == 200
    mv1 = put.json()["model_version_id"]

    run = client.post(
        f"/companies/{company_id}/packs/{pack_id}/run",
        json={"inputs": inputs, "variant": "base"},
    )
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["pack_id"] == pack_id
    assert body["model_version_id"] == mv1
    assert body["calculation_run_id"]
    assert body["scenario_id"]
    assert body["result_hash"]
    assert body["inputs_hash"]
    assert isinstance(body["actual_keys"], list)
    assert body["financing_need"] is not None
    assert isinstance(body["financing_need"]["min_cash"], str)
    assert isinstance(body["results"]["cash_flow"], list)
    assert len(body["results"]["cash_flow"]) >= 1
    assert _find_floats(body["results"]) == []
    assert _find_floats(body["financing_need"]) == []
    assert _find_floats(body.get("investment_metrics")) == []

    cur = client.get(f"/companies/{company_id}/snapshot")
    assert cur.status_code == 200
    assert cur.json()["model_version_id"] == mv1

    got = client.get(f"/calculation-runs/{body['calculation_run_id']}")
    assert got.status_code == 200
    assert got.json()["status"] == "completed"
    assert got.json()["results"]["result_hash"] == body["result_hash"]
    assert _find_floats(got.json()["results"]) == []
    assert _find_floats(got.json()["calculation_input"]) == []


@pytest.mark.parametrize("pack_id,inputs", _pack_cases())
def test_each_pack_three_variants(client: TestClient, pack_id: str, inputs: dict) -> None:
    company_id = client.post("/companies", json={"name": f"V-{pack_id}"}).json()["id"]
    put = client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": _base_twin()},
    )
    mv1 = put.json()["model_version_id"]
    for variant in ("base", "conservative", "adverse"):
        r = client.post(
            f"/companies/{company_id}/packs/{pack_id}/run",
            json={"inputs": inputs, "variant": variant},
        )
        assert r.status_code == 200, f"{pack_id}/{variant}: {r.text}"
        assert r.json()["variant"] == variant
        assert r.json()["model_version_id"] == mv1
        assert _find_floats(r.json()["results"]) == []
    assert client.get(f"/companies/{company_id}/snapshot").json()["model_version_id"] == mv1
