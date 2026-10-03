"""F5 — API new_site flow with persisted CalculationRun."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.db import Store
from financetwin_api.main import create_app
from financetwin_api.ops import build_op_to_dict
from financetwin_engine.mapper.build_ops import BuildOp


@pytest.fixture()
def client(tmp_path: Path):
    db = tmp_path / "test.sqlite"
    application = create_app(str(db))
    with TestClient(application) as c:
        yield c


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "store.sqlite"


def _minimal_snapshot():
    return {
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


def _new_site_inputs():
    return {
        "site_name": "Tienda API",
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


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "engine_version" in r.json()


def test_new_site_api_flow_persists_run(client: TestClient) -> None:
    c = client.post("/companies", json={"name": "Demo SL"})
    assert c.status_code == 200
    company_id = c.json()["id"]

    s = client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": _minimal_snapshot(), "label": "v1"},
    )
    assert s.status_code == 200
    mv1 = s.json()["model_version_id"]

    run = client.post(
        f"/companies/{company_id}/packs/new_site/run",
        json={"inputs": _new_site_inputs(), "variant": "base"},
    )
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["model_version_id"] == mv1
    assert body["calculation_run_id"]
    assert body["scenario_id"]
    assert body["result_hash"]
    assert isinstance(body["investment_metrics"]["npv"], str)
    assert isinstance(body["financing_need"]["min_cash"], str)
    assert isinstance(body["results"]["cash_flow"][0]["capex_paid"], str)
    assert body["results"]["cash_flow"][0]["capex_paid"] == "350000.00"
    assert _find_floats(body["results"]) == []
    assert _find_floats(body["investment_metrics"]) == []

    cur = client.get(f"/companies/{company_id}/snapshot")
    assert cur.status_code == 200
    assert cur.json()["model_version_id"] == mv1

    got = client.get(f"/calculation-runs/{body['calculation_run_id']}")
    assert got.status_code == 200
    assert got.json()["status"] == "completed"
    assert got.json()["results"]["cash_flow"][0]["loan_drawdowns"] == "200000.00"
    assert got.json()["results"]["result_hash"] == body["result_hash"]
    assert _find_floats(got.json()["results"]) == []
    assert _find_floats(got.json()["calculation_input"]) == []


def test_new_site_all_variants(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "V"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": _minimal_snapshot()},
    )
    npvs = {}
    for variant in ("base", "conservative", "adverse"):
        r = client.post(
            f"/companies/{company_id}/packs/new_site/run",
            json={"inputs": _new_site_inputs(), "variant": variant},
        )
        assert r.status_code == 200, r.text
        npvs[variant] = Decimal(r.json()["investment_metrics"]["npv"])
    assert npvs["adverse"] < npvs["conservative"] < npvs["base"]


def test_model_version_parent_chain(db_path: Path) -> None:
    store = Store(db_path)
    company = store.create_company("Chain Co")
    mv1 = store.put_current_snapshot(company.id, _minimal_snapshot(), label="v1")
    meta1 = store.get_model_version_meta(mv1)
    assert meta1 is not None
    assert meta1["parent_id"] is None
    assert meta1["is_current"] == 1

    mv2 = store.put_current_snapshot(company.id, _minimal_snapshot(), label="v2")
    meta2 = store.get_model_version_meta(mv2)
    assert meta2 is not None
    assert meta2["parent_id"] == mv1
    assert meta2["is_current"] == 1
    assert store.get_model_version_meta(mv1)["is_current"] == 0
    assert store.get_current_snapshot(company.id)[0] == mv2


def test_build_op_dict_serializes_decimals() -> None:
    op = BuildOp(
        op="add_entity",
        entity_type="loans",
        entity_id="L1",
        payload={
            "principal": Decimal("1000.00"),
            "annual_interest_rate": Decimal("0.05"),
        },
    )
    d = build_op_to_dict(op)
    json.dumps(d)  # must not raise
    assert d["payload"]["principal"] == "1000.00"
    assert d["payload"]["annual_interest_rate"] == "0.05"


def test_funding_error_via_api(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "X"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": _minimal_snapshot()},
    )
    bad = dict(_new_site_inputs())
    bad["equity_amount"] = "1000"
    r = client.post(
        f"/companies/{company_id}/packs/new_site/run",
        json={"inputs": bad, "variant": "base"},
    )
    assert r.status_code == 400


def test_put_snapshot_rejects_bad_schema(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "X"}).json()["id"]
    r = client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": {"schema_version": "9.9", "company": {"currency": "EUR"}}},
    )
    assert r.status_code == 400


def test_run_without_snapshot_is_400(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Empty"}).json()["id"]
    r = client.post(
        f"/companies/{company_id}/packs/new_site/run",
        json={"inputs": _new_site_inputs()},
    )
    assert r.status_code == 400
