"""P15 — Flujo humano: onboarding, Resultado en nav, formatters, sin Math. financiero."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p15.sqlite"))
    with TestClient(application) as c:
        yield c


def test_ui_p15_onboarding(client: TestClient) -> None:
    html = client.get("/").text
    assert 'id="home-onboard"' in html
    assert 'id="btn-demo-home"' in html
    assert 'id="btn-create-home"' in html
    assert 'id="btn-create-top"' in html
    assert "— Seleccionar —" in html
    assert "Crear mi empresa" in html or "Crear empresa" in html
    assert "Empezar →" in html
    assert 'id="nav-report"' in html
    assert 'id="demo_banner"' in html
    assert 'id="home-company-card"' in html


def test_ui_p15_formatters_and_no_math(client: TestClient) -> None:
    js = client.get("/static/app.js").text
    assert "fmtMoney" in js
    assert "fmtRate" in js
    assert "fmtMetric" in js
    assert "updateHomeGates" in js
    assert "updateNavReport" in js
    assert "Math." not in js
    assert "average(" not in js.lower()


def test_ui_p15_critical_ids(client: TestClient) -> None:
    html = client.get("/").text
    for eid in (
        "btn-run",
        "btn-demo",
        "btn-compare",
        "btn-register-decision",
        "btn-download-report",
        "sec-home",
        "hero_value",
        "company_select",
        "metrics",
        "actuals-block",
        "app-nav",
    ):
        assert f'id="{eid}"' in html, eid
    assert 'id="metrics"' in html
    # metrics must not be stuck hidden in markup
    assert 'id="metrics" class="metrics" hidden' not in html
