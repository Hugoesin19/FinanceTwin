"""P14 — UX producto perfecto: shell único, 3 jobs, hero, sin Math."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p14.sqlite"))
    with TestClient(application) as c:
        yield c


def test_ui_p14_shell_and_home(client: TestClient) -> None:
    html = client.get("/").text
    css = client.get("/static/styles.css").text
    js = client.get("/static/app.js").text

    assert 'id="app-nav"' in html
    assert 'id="product-nav"' not in html
    assert 'id="stepper"' not in html
    assert 'id="context-bar"' in html
    assert 'id="company_select"' in html
    assert 'id="sec-home"' in html
    assert 'id="home-btn-decide"' in html
    assert 'id="home-btn-liquidity"' in html
    assert "job-card" in html
    assert html.count('class="job-card"') >= 3

    assert ".app-sidebar" in css
    assert ".result-hero" in css or ".hero-value" in css
    assert "Fraunces" in css or "fraunces" in css.lower()

    assert "setWizardStep" in js
    assert "renderPackCards" in js
    assert "hero_value" in js or "hero_label" in js
    assert "Math." not in js
    assert "average(" not in js.lower()


def test_ui_p14_wizard_and_result_hero(client: TestClient) -> None:
    html = client.get("/").text

    assert 'id="wizard-steps"' in html
    assert 'id="wiz-pane-1"' in html
    assert 'id="wiz-pane-2"' in html
    assert 'id="wiz-pane-3"' in html
    assert 'id="pack_cards"' in html
    assert 'id="hero_metric"' in html
    assert 'id="hero_value"' in html
    assert 'id="hero_label"' in html
    assert "class=\"disclose\"" in html or "class='disclose'" in html


def test_ui_p14_critical_api_ids(client: TestClient) -> None:
    html = client.get("/").text
    for eid in (
        "btn-run",
        "btn-compare",
        "btn-compare-report",
        "btn-sensitivity",
        "btn-download-report",
        "btn-demo",
        "btn-register-decision",
        "btn-record-actuals",
        "btn-load-bias",
        "btn-calib-preview",
        "btn-apply-calib",
        "btn-import-csv",
        "sec-home",
        "sec-report",
        "sec-twin-loop",
        "sec-import",
        "pack_id",
        "pack_fields",
        "metrics",
        "compare",
        "policies",
        "cash",
        "trace",
    ):
        assert f'id="{eid}"' in html, eid
