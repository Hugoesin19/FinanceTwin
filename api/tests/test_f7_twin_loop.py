"""F7 — V5 Twin Loop: ActualResult + BiasProfile + calibración n≥3."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from financetwin_engine.analytics.bias import calibrate_value, deviation_pct

SNAP = {
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

INPUTS = {
    "site_name": "Tienda V5",
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
    app = create_app(str(tmp_path / "f7.sqlite"))
    with TestClient(app) as c:
        yield c


def _run_new_site(client: TestClient, company_id: str) -> str:
    r = client.post(
        f"/companies/{company_id}/packs/new_site/run",
        json={"inputs": INPUTS, "variant": "base"},
    )
    assert r.status_code == 200, r.text
    return r.json()["calculation_run_id"]


def _executed_decision(
    client: TestClient, company_id: str, title: str, run_id: str
) -> str:
    d = client.post(
        f"/companies/{company_id}/decisions",
        json={
            "title": title,
            "decision_pack_id": "new_site",
            "decision_date": "2027-01-15",
            "calculation_run_id": run_id,
            "status": "executed",
            "rationale": "Decisión piloto V5",
            "owner_user_id": "tester",
        },
    )
    assert d.status_code == 200, d.text
    body = d.json()
    assert body["status"] == "executed"
    assert body["number"] >= 1
    assert len(body["milestones"]) == 3
    return body["id"]


def test_v5_actuals_bias_and_calibration_gate(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "V5 Co"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": SNAP},
    )

    # --- n=0: calibración NO ofrecida ---
    preview0 = client.post(
        f"/companies/{company_id}/packs/new_site/calibration/preview",
        json={"inputs": INPUTS},
    )
    assert preview0.status_code == 200
    assert preview0.json()["offered"] is False

    forecasts = ["40000", "40000", "40000"]
    actuals = ["36000", "32800", "32000"]  # bias 0.10, 0.18, 0.20 → median 0.18

    decision_ids = []
    for i, (f, a) in enumerate(zip(forecasts, actuals)):
        run_id = _run_new_site(client, company_id)
        did = _executed_decision(client, company_id, f"Apertura #{i+1}", run_id)
        decision_ids.append(did)

        rec = client.post(
            f"/decisions/{did}/actuals",
            json={
                "period_year_month": f"2027-0{6+i}",
                "items": [
                    {
                        "variable_key": "sales_monthly",
                        "forecast_value": f,
                        "actual_value": a,
                        "source": "manual",
                    }
                ],
            },
        )
        assert rec.status_code == 200, rec.text
        recorded = rec.json()["recorded"][0]
        expected = deviation_pct(f, a).deviation_pct
        assert recorded["deviation_pct"] is not None
        assert abs(Decimal(recorded["deviation_pct"]) - expected) < Decimal("1e-9")

        profiles = client.get(
            f"/companies/{company_id}/packs/new_site/bias-profiles"
        ).json()["profiles"]
        sales = next(p for p in profiles if p["variable_key"] == "sales_monthly")
        assert sales["n_observations"] == i + 1

        preview = client.post(
            f"/companies/{company_id}/packs/new_site/calibration/preview",
            json={"inputs": INPUTS},
        ).json()
        if i + 1 < 3:
            assert preview["offered"] is False
        else:
            assert preview["offered"] is True
            assert preview["calibrated_inputs"] is not None
            assert preview["calibrated_inputs"]["sales_run_rate"] == str(
                calibrate_value("40000", sales["median_bias"])
            )

    # BiasProfile mediana = 0.18
    profiles = client.get(
        f"/companies/{company_id}/packs/new_site/bias-profiles"
    ).json()["profiles"]
    sales = next(p for p in profiles if p["variable_key"] == "sales_monthly")
    assert sales["n_observations"] == 3
    assert Decimal(sales["median_bias"]) == Decimal("0.18")
    assert sales["direction"] == "overestimate"
    assert sales["confidence"] == "medium"


def test_actuals_rejected_if_not_executed(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "X"}).json()["id"]
    client.put(f"/companies/{company_id}/snapshot", json={"snapshot": SNAP})
    run_id = _run_new_site(client, company_id)
    d = client.post(
        f"/companies/{company_id}/decisions",
        json={
            "title": "Drafty",
            "decision_pack_id": "new_site",
            "decision_date": "2027-01-15",
            "calculation_run_id": run_id,
            "status": "approved",
            "rationale": "ok",
        },
    )
    assert d.status_code == 200
    did = d.json()["id"]
    bad = client.post(
        f"/decisions/{did}/actuals",
        json={
            "period_year_month": "2027-06",
            "items": [
                {
                    "variable_key": "sales_monthly",
                    "forecast_value": "1",
                    "actual_value": "1",
                }
            ],
        },
    )
    assert bad.status_code == 400

    # transition approved → executed then OK
    ex = client.post(f"/decisions/{did}/status", json={"status": "executed"})
    assert ex.status_code == 200
    assert ex.json()["status"] == "executed"


def test_cannot_reopen_executed(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Y"}).json()["id"]
    client.put(f"/companies/{company_id}/snapshot", json={"snapshot": SNAP})
    run_id = _run_new_site(client, company_id)
    did = _executed_decision(client, company_id, "Done", run_id)
    r = client.post(f"/decisions/{did}/status", json={"status": "approved"})
    assert r.status_code == 400


def test_unknown_variable_key_rejected(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Z"}).json()["id"]
    client.put(f"/companies/{company_id}/snapshot", json={"snapshot": SNAP})
    run_id = _run_new_site(client, company_id)
    did = _executed_decision(client, company_id, "Z", run_id)
    r = client.post(
        f"/decisions/{did}/actuals",
        json={
            "period_year_month": "2027-06",
            "items": [
                {
                    "variable_key": "invented_metric",
                    "forecast_value": "1",
                    "actual_value": "2",
                }
            ],
        },
    )
    assert r.status_code == 400
    assert "variable_key" in r.json()["detail"]


def test_forecast_zero_null_deviation_and_warning(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "W"}).json()["id"]
    client.put(f"/companies/{company_id}/snapshot", json={"snapshot": SNAP})
    run_id = _run_new_site(client, company_id)
    did = _executed_decision(client, company_id, "W", run_id)
    r = client.post(
        f"/decisions/{did}/actuals",
        json={
            "period_year_month": "2027-06",
            "items": [
                {
                    "variable_key": "sales_monthly",
                    "forecast_value": "0",
                    "actual_value": "100",
                }
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["recorded"][0]["deviation_pct"] is None
    assert body["warnings"]
    # null deviation no cuenta en BiasProfile
    profiles = client.get(
        f"/companies/{company_id}/packs/new_site/bias-profiles"
    ).json()["profiles"]
    assert profiles == []


def test_n_counts_decisions_not_periods(client: TestClient) -> None:
    """Varios periodos en la misma decisión = 1 observación de bias."""
    company_id = client.post("/companies", json={"name": "N"}).json()["id"]
    client.put(f"/companies/{company_id}/snapshot", json={"snapshot": SNAP})
    run_id = _run_new_site(client, company_id)
    did = _executed_decision(client, company_id, "One", run_id)
    for ym, actual in (("2027-06", "36000"), ("2027-07", "32800"), ("2027-08", "32000")):
        r = client.post(
            f"/decisions/{did}/actuals",
            json={
                "period_year_month": ym,
                "items": [
                    {
                        "variable_key": "sales_monthly",
                        "forecast_value": "40000",
                        "actual_value": actual,
                    }
                ],
            },
        )
        assert r.status_code == 200
    profiles = client.get(
        f"/companies/{company_id}/packs/new_site/bias-profiles"
    ).json()["profiles"]
    sales = next(p for p in profiles if p["variable_key"] == "sales_monthly")
    assert sales["n_observations"] == 1
    # latest period actual 32000 → bias 0.20
    assert Decimal(sales["median_bias"]) == Decimal("0.20")
    preview = client.post(
        f"/companies/{company_id}/packs/new_site/calibration/preview",
        json={"inputs": INPUTS},
    ).json()
    assert preview["offered"] is False


def test_invalid_pack_and_status(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Bad"}).json()["id"]
    client.put(f"/companies/{company_id}/snapshot", json={"snapshot": SNAP})
    run_id = _run_new_site(client, company_id)
    bad_pack = client.post(
        f"/companies/{company_id}/decisions",
        json={
            "title": "x",
            "decision_pack_id": "not_a_pack",
            "decision_date": "2027-01-15",
            "calculation_run_id": run_id,
            "status": "executed",
            "rationale": "x",
        },
    )
    assert bad_pack.status_code == 400
    bad_status = client.post(
        f"/companies/{company_id}/decisions",
        json={
            "title": "x",
            "decision_pack_id": "new_site",
            "decision_date": "2027-01-15",
            "calculation_run_id": run_id,
            "status": "done",
            "rationale": "x",
        },
    )
    assert bad_status.status_code == 400


def test_calibration_pack_without_mapping_not_offered(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Fin"}).json()["id"]
    r = client.post(
        f"/companies/{company_id}/packs/financing/calibration/preview",
        json={"inputs": {"loan_amount": "100000"}},
    )
    assert r.status_code == 200
    assert r.json()["offered"] is False
    assert "mapping" in (r.json()["reason"] or "")
