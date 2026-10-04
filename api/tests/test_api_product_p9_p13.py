"""P9–P13 — producto profesional uso C (twin quality, informe, home, liquidez)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app
from financetwin_api.twin_quality import assess_twin_quality
from tests.test_ui_p2 import UI_PACK_INPUTS, UI_TWIN_WITH_STREAMS


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p913.sqlite"))
    with TestClient(application) as c:
        yield c


def test_twin_quality_checklist() -> None:
    q = assess_twin_quality(UI_TWIN_WITH_STREAMS)
    assert q["summary"]["revenue_stream_count"] == 1
    assert q["ready_for_packs"]["liquidity_plan"] is True
    assert all("ok" in c and "label" in c for c in q["checks"])


def test_api_twin_quality_and_list_companies(client: TestClient) -> None:
    assert client.get("/companies").json()["companies"] == []
    cid = client.post("/companies", json={"name": "Q"}).json()["id"]
    client.put(
        f"/companies/{cid}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS},
    )
    listed = client.get("/companies").json()["companies"]
    assert len(listed) == 1
    assert listed[0]["id"] == cid
    q = client.get(f"/companies/{cid}/twin-quality")
    assert q.status_code == 200
    body = q.json()
    assert body["quality"]["ready_for_packs"]["new_site"] is True
    snap = client.get(f"/companies/{cid}/snapshot").json()
    assert "quality" in snap


def test_executive_report_html(client: TestClient) -> None:
    cid = client.post("/companies", json={"name": "R"}).json()["id"]
    client.put(
        f"/companies/{cid}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS},
    )
    run = client.post(
        f"/companies/{cid}/packs/new_site/run",
        json={"inputs": UI_PACK_INPUTS["new_site"], "variant": "base"},
    )
    assert run.status_code == 200
    rep = client.post(
        f"/companies/{cid}/reports/executive",
        json={
            "run": run.json(),
            "company_name": "R",
            "compare": None,
        },
    )
    assert rep.status_code == 200
    assert "text/html" in rep.headers["content-type"]
    assert "attachment" in rep.headers.get("content-disposition", "")
    assert "Informe ejecutivo" in rep.text
    assert run.json()["investment_metrics"]["npv"] in rep.text
    assert "Finance Twin" in rep.text


def test_liquidity_pack_run(client: TestClient) -> None:
    cid = client.post("/companies", json={"name": "L"}).json()["id"]
    client.put(
        f"/companies/{cid}/snapshot",
        json={"snapshot": UI_TWIN_WITH_STREAMS},
    )
    r = client.post(
        f"/companies/{cid}/packs/liquidity_plan/run",
        json={"inputs": UI_PACK_INPUTS["liquidity_plan"], "variant": "base"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pack_id"] == "liquidity_plan"
    assert isinstance(body["financing_need"]["min_cash"], str)


def test_ui_p9_p13_smoke(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    assert 'id="sec-home"' in html
    assert 'id="app-nav"' in html
    assert 'id="twin_quality_panel"' in html
    assert 'id="btn-download-report"' in html
    assert 'id="home-btn-liquidity"' in html
    assert 'id="company_select"' in html
    assert 'id="forecast-actual-table"' in html
    assert "assess_twin_quality" not in js  # quality from API
    assert "downloadExecutiveReport" in js
    assert "refreshHome" in js
    assert "liquidity" in js
    assert "Math." not in js
