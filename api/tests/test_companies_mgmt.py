"""Gestión de empresas: renombrar y borrar."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "co.sqlite"))
    with TestClient(application) as c:
        yield c


def test_rename_and_delete_company(client: TestClient) -> None:
    a = client.post("/companies", json={"name": "A SL"}).json()
    b = client.post("/companies", json={"name": "Demo Tienda SL"}).json()
    client.put(
        f"/companies/{a['id']}/snapshot",
        json={
            "snapshot": {
                "schema_version": "1.0",
                "company": {
                    "currency": "EUR",
                    "opening_cash": "1",
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
        },
    )
    ren = client.patch(f"/companies/{a['id']}", json={"name": "A Renombrada"})
    assert ren.status_code == 200
    assert ren.json()["name"] == "A Renombrada"

    deleted = client.delete(f"/companies/{b['id']}")
    assert deleted.status_code == 200
    listed = {c["id"] for c in client.get("/companies").json()["companies"]}
    assert a["id"] in listed
    assert b["id"] not in listed

    gone = client.get(f"/companies/{b['id']}/snapshot")
    assert gone.status_code == 404


def test_ui_companies_mgmt_markup(client: TestClient) -> None:
    html = client.get("/").text
    assert 'id="sec-companies-mgmt"' in html
    assert 'id="companies-mgmt-table"' in html
    assert 'id="btn-delete-all-demos"' in html
    assert "Usar" in html or "Acciones" in html
    js = client.get("/static/app.js").text
    assert "deleteCompanyUi" in js
    assert "useCompany" in js
    assert "createCompanyShell" in js
    assert "renting_as_cost" in js
    assert "variant_explain" in html or "Sí influye" in html
