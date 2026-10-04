"""P5 — import twin CSV → ModelVersion current."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.csv_import import TwinCsvError, parse_and_validate_twin_csv
from financetwin_api.main import create_app

API_ROOT = Path(__file__).resolve().parents[1]
OK_CSV = (API_ROOT / "fixtures" / "synthetic_twin_ok.csv").read_text(encoding="utf-8")
BAD_CSV = (API_ROOT / "fixtures" / "synthetic_twin_bad.csv").read_text(encoding="utf-8")
TEMPLATE = API_ROOT / "templates" / "twin_snapshot_template.csv"


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p5.sqlite"))
    with TestClient(application) as c:
        yield c


def test_parse_ok_fixture() -> None:
    snap = parse_and_validate_twin_csv(OK_CSV)
    assert snap["schema_version"] == "1.0"
    assert snap["company"]["opening_cash"] == "80000"
    assert snap["revenue_streams"][0]["id"] == "R0"
    assert snap["cost_items"][0]["id"] == "C0"


def test_parse_bad_currency() -> None:
    with pytest.raises((TwinCsvError, ValueError)):
        parse_and_validate_twin_csv(BAD_CSV)


def test_template_file_exists() -> None:
    assert TEMPLATE.is_file()
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "# SECTION company" in text
    assert "# SECTION fiscal" in text
    assert "# SECTION policies" in text


def test_download_template(client: TestClient) -> None:
    r = client.get("/templates/twin_snapshot_template.csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "# SECTION company" in r.text


def test_import_happy_creates_new_model_version(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Import Co"}).json()["id"]
    # baseline empty-ish twin via PUT
    put1 = client.put(
        f"/companies/{company_id}/snapshot",
        json={
            "snapshot": {
                "schema_version": "1.0",
                "company": {"currency": "EUR", "opening_cash": "1000"},
                "fiscal": {
                    "vat_rate": "0",
                    "vat_settlement": "monthly",
                    "vat_payment_lag_months": 0,
                    "corp_tax_rate": "0",
                    "corp_tax_payment_mode": "none",
                },
                "policies": {"min_cash": "0"},
            },
            "label": "manual",
        },
    )
    assert put1.status_code == 200
    mv1 = put1.json()["model_version_id"]

    r = client.post(
        f"/companies/{company_id}/imports/twin-csv",
        files={"file": ("synthetic_twin_ok.csv", OK_CSV.encode("utf-8"), "text/csv")},
        data={"label": "p5-ok"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_version_id"] != mv1
    assert body["is_current"] is True
    assert body["snapshot"]["company"]["opening_cash"] == "80000"
    assert body["snapshot"]["revenue_streams"][0]["base_monthly_revenue"] == "30000"

    cur = client.get(f"/companies/{company_id}/snapshot")
    assert cur.status_code == 200
    assert cur.json()["model_version_id"] == body["model_version_id"]
    assert cur.json()["snapshot"]["cost_items"][0]["id"] == "C0"


def test_import_without_prior_snapshot(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Fresh"}).json()["id"]
    r = client.post(
        f"/companies/{company_id}/imports/twin-csv",
        files={"file": ("ok.csv", OK_CSV.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200, r.text
    assert client.get(f"/companies/{company_id}/snapshot").json()["model_version_id"] == r.json()[
        "model_version_id"
    ]


def test_import_404_unknown_company(client: TestClient) -> None:
    r = client.post(
        "/companies/00000000-0000-0000-0000-000000000000/imports/twin-csv",
        files={"file": ("ok.csv", OK_CSV.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 404


def test_import_invalid_returns_400(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "Bad"}).json()["id"]
    r = client.post(
        f"/companies/{company_id}/imports/twin-csv",
        files={"file": ("bad.csv", BAD_CSV.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert isinstance(detail, dict)
    assert detail.get("code") in ("snapshot_invalid", "csv_format")
    assert "message" in detail


def test_import_malformed_csv_400(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "X"}).json()["id"]
    r = client.post(
        f"/companies/{company_id}/imports/twin-csv",
        files={"file": ("x.csv", b"not a sectioned csv", "text/csv")},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "csv_format"


def test_ui_p5_smoke(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert 'id="sec-import"' in html
    assert 'id="btn-import-csv"' in html
    assert "/templates/twin_snapshot_template.csv" in html
    assert "importTwinCsv" in js
    assert "/imports/twin-csv" in js
    assert "FormData" in js
    assert "clearReport" in js
    assert "Math." not in js
