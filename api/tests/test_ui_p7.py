"""P7 — Usabilidad del camino crítico (actualizado P14: sidebar, demo, ids)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p7.sqlite"))
    with TestClient(application) as c:
        yield c


def test_ui_p7_smoke(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    css = client.get("/static/styles.css").text

    # P14: una sola navegación (sidebar); sin stepper duplicado
    assert 'id="app-nav"' in html
    assert 'id="stepper"' not in html
    assert 'id="btn-demo"' in html
    assert "Cargar demo" in html
    assert "Resultado" in html
    assert 'id="btn-run"' in html
    assert 'id="btn-compare"' in html
    assert 'id="btn-sensitivity"' in html
    assert 'id="btn-register-decision"' in html

    assert "loadDemo" in js
    assert "goToStep" in js
    assert "humanizeError" in js
    assert "formatApiDetail" in js
    assert "METRIC_LABELS" in js
    assert "Math." not in js
    assert "average(" not in js.lower()

    assert ".app-sidebar" in css
    assert ".side-link.active" in css


def test_ui_p7_ids_stable_for_prior_smokes(client: TestClient) -> None:
    html = client.get("/").text
    for eid in (
        "company_name",
        "opening_cash",
        "pack_id",
        "pack_fields",
        "sec-report",
        "sec-twin-loop",
        "sec-import",
        "btn-import-csv",
        "metrics",
        "compare",
        "policies",
        "cash",
        "trace",
        "sensitivity_out",
    ):
        assert f'id="{eid}"' in html, eid
