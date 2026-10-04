"""P6 — API sensibilidad + smoke UI."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from tests.test_ui_p2 import UI_PACK_INPUTS, UI_TWIN_WITH_STREAMS


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p6.sqlite"))
    with TestClient(application) as c:
        yield c


def test_sensitivity_new_site(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "P6"}).json()["id"]
    put = client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS},
    )
    mv = put.json()["model_version_id"]
    r = client.post(
        f"/companies/{company_id}/packs/new_site/sensitivity",
        json={
            "inputs": UI_PACK_INPUTS["new_site"],
            "variant": "base",
            "include": ["direct", "inverse", "stress"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pack_id"] == "new_site"
    assert body["model_version_id"] == mv
    assert isinstance(body["direct"]["base"]["npv"], str)
    assert body["direct"]["rows"]
    assert body["inverse"]["rows"]
    assert body["stress"]["rows"]
    # MV intact
    assert (
        client.get(f"/companies/{company_id}/snapshot").json()["model_version_id"]
        == mv
    )
    # no floats
    def walk(o):
        if isinstance(o, float):
            raise AssertionError("float")
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(body)
    sales = [
        r
        for r in body["direct"]["rows"]
        if r.get("variable") == "sales_run_rate" and not r.get("skipped")
    ]
    assert len(sales) == 2
    assert Decimal(sales[0]["metrics"]["npv"]) != Decimal(sales[1]["metrics"]["npv"])


def test_sensitivity_financing_rejected(client: TestClient) -> None:
    company_id = client.post("/companies", json={"name": "X"}).json()["id"]
    client.put(
        f"/companies/{company_id}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS},
    )
    r = client.post(
        f"/companies/{company_id}/packs/financing/sensitivity",
        json={"inputs": UI_PACK_INPUTS["financing"], "variant": "base"},
    )
    assert r.status_code == 400


def test_ui_p6_smoke(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert 'id="btn-sensitivity"' in html
    assert "sensitivity" in html.lower()
    assert "runSensitivity" in js
    assert "/sensitivity" in js
    assert '!== "new_site"' in js or "!== 'new_site'" in js
    assert "Math." not in js
