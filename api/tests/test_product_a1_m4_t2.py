"""Producto decisión + motor: A1/D1/M1–M4/T1–T2 smoke."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from financetwin_api.sabi_import import parse_sabi_csv_text


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "prod.sqlite"))
    with TestClient(application) as c:
        yield c


def _twin():
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
        "policies": {"min_cash": "10000"},
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


def _new_site_inputs():
    return {
        "site_name": "Tienda Test",
        "open_year_month": "2027-01",
        "capex_total": "200000",
        "sales_run_rate": "40000",
        "gross_margin_pct": "0.40",
        "rent_monthly": "4000",
        "other_opex_monthly": "1000",
        "headcount": 2,
        "employer_cost_per_person": "2500",
        "debt_amount": "100000",
        "equity_amount": "100000",
        "loan_term_months": 60,
        "loan_annual_rate": "0.055",
        "horizon_months": 24,
        "discount_rate_annual": "0.08",
        "collection_days": 0,
    }


def _company_with_twin(client: TestClient) -> str:
    c = client.post("/companies", json={"name": "Prod SL"}).json()
    client.put(f"/companies/{c['id']}/snapshot", json={"snapshot": _twin(), "label": "t"})
    return c["id"]


def test_ui_a1_tradeoff_and_report_blocks(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert 'id="tradeoff_box"' in html
    assert 'id="runway_line"' in html
    assert 'id="dscr_block"' in html
    assert 'id="scorecard_block"' in html
    assert 'id="tornado-block"' in html
    assert 'id="montecarlo-block"' in html
    assert "renderTradeoff" in js
    assert "runTornado" in js
    assert "runMonteCarlo" in js
    assert "previewSabi" in js
    assert "showDataPath" in js


def test_a2_liquidity_no_presets_happy_path(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert "liquidity_presets" not in html
    assert "data-liq-preset" not in html
    assert "applyLiquidityPreset" not in js
    assert "Sin presets" in js or "sin presets" in js.lower() or 'value: "0"' in js


def test_a3_twin_loop_human_copy(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert 'id="bias_human"' in html
    assert "DIRECTION_LABELS" in js
    assert "Anotar lo que ocurrió" in html


def test_d1_sabi_csv_preview_confirm(client: TestClient) -> None:
    cid = _company_with_twin(client)
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "sabi_pgc_anon.csv"
    text = fixture.read_text(encoding="utf-8")
    draft = parse_sabi_csv_text(text, year_month="2025-01")
    assert draft["confirm_required"] is True
    assert float(draft["derived"]["opening_cash"]) == 125000.0
    assert float(draft["derived"]["revenue_monthly"]) == 100000.0
    assert draft["derived"]["bank_debt_hint"] is not None

    files = {"file": ("sabi_pgc_anon.csv", text.encode("utf-8"), "text/csv")}
    preview = client.post(
        f"/companies/{cid}/imports/sabi-preview",
        files=files,
        data={"year_month": "2025-01"},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["snapshot"]["company"]["opening_cash"] == "125000.00" or body[
        "snapshot"
    ]["company"]["opening_cash"].startswith("125000")

    confirm = client.post(
        f"/companies/{cid}/imports/sabi-confirm",
        json={"snapshot": body["snapshot"], "label": "sabi-test"},
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["is_current"] is True

    liq = client.post(
        f"/companies/{cid}/packs/liquidity_plan/run",
        json={
            "inputs": {
                "horizon_months": 6,
                "anchor_year_month": "2025-01",
                "sales_adjustment_pct": "-0.10",
            },
            "variant": "base",
        },
    )
    assert liq.status_code == 200, liq.text
    assert "financing_need" in liq.json()


def test_m1_tornado_and_runway(client: TestClient) -> None:
    cid = _company_with_twin(client)
    run = client.post(
        f"/companies/{cid}/packs/new_site/run",
        json={"inputs": _new_site_inputs(), "variant": "base"},
    ).json()
    assert "months_below_policy" in run["financing_need"]
    assert "scorecard" in run

    tornado = client.post(
        f"/companies/{cid}/packs/new_site/tornado",
        json={"inputs": _new_site_inputs(), "variant": "base", "metric": "npv"},
    )
    assert tornado.status_code == 200, tornado.text
    bars = tornado.json()["bars"]
    assert any(not b.get("skipped") for b in bars)


def test_m2_dscr_on_debt_run(client: TestClient) -> None:
    cid = _company_with_twin(client)
    run = client.post(
        f"/companies/{cid}/packs/new_site/run",
        json={"inputs": _new_site_inputs(), "variant": "base"},
    ).json()
    assert "dscr" in run
    # Con deuda debería haber servicio en algún mes
    assert run["dscr"]["available"] is True
    assert run["dscr"]["min_dscr"] is not None


def test_m3_montecarlo_seeded(client: TestClient) -> None:
    cid = _company_with_twin(client)
    body = {
        "inputs": _new_site_inputs(),
        "variant": "base",
        "n_sims": 20,
        "seed": 42,
    }
    a = client.post(f"/companies/{cid}/packs/new_site/montecarlo", json=body).json()
    b = client.post(f"/companies/{cid}/packs/new_site/montecarlo", json=body).json()
    assert a["npv_p50"] == b["npv_p50"]
    assert a["disclaimer"]
    assert "bajo los rangos" in a["disclaimer"].lower()
    assert "no es una probabilidad" in a["disclaimer"].lower()


def test_m4_scorecard_and_report(client: TestClient) -> None:
    cid = _company_with_twin(client)
    run = client.post(
        f"/companies/{cid}/packs/new_site/run",
        json={"inputs": _new_site_inputs(), "variant": "base"},
    ).json()
    sc = client.post(
        f"/companies/{cid}/scorecard",
        json={"run": run},
    ).json()
    assert sc["scorecard"]["overall"] in ("Favorable", "Mixto", "Desfavorable")
    report = client.post(
        f"/companies/{cid}/reports/executive",
        json={
            "run": run,
            "company_name": "Prod SL",
            "scorecard": sc["scorecard"],
        },
    )
    assert report.status_code == 200
    html = report.text
    assert "Memo de decisión" in html
    assert "Scorecard" in html or "Semáforo" in html


def test_t1_health_and_demo_bootstrap(client: TestClient) -> None:
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"
    boot = client.post("/demo/bootstrap")
    assert boot.status_code == 200, boot.text
    data = boot.json()
    assert data["company"]["id"]
    assert data["run"]["pack_id"] == "new_site"
    assert data["run"]["investment_metrics"]


def test_t2_org_isolation(client: TestClient) -> None:
    a = client.post("/auth/signup", json={"name": "Org A"}).json()
    b = client.post("/auth/signup", json={"name": "Org B"}).json()
    ha = {"X-Org-Token": a["token"]}
    hb = {"X-Org-Token": b["token"]}

    ca = client.post("/companies", json={"name": "Solo A"}, headers=ha).json()
    cb = client.post("/companies", json={"name": "Solo B"}, headers=hb).json()

    listed_a = client.get("/companies", headers=ha).json()["companies"]
    listed_b = client.get("/companies", headers=hb).json()["companies"]
    ids_a = {c["id"] for c in listed_a}
    ids_b = {c["id"] for c in listed_b}
    assert ca["id"] in ids_a
    assert cb["id"] not in ids_a
    assert cb["id"] in ids_b
    assert ca["id"] not in ids_b

    deny = client.get(f"/companies/{ca['id']}/snapshot", headers=hb)
    assert deny.status_code == 404
