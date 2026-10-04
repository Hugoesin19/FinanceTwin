"""P8 — Claridad + UI Atlantic Ledger (compare, sensibilidad, print; shell P14)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "p8.sqlite"))
    with TestClient(application) as c:
        yield c


def test_ui_p8_smoke(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    css = client.get("/static/styles.css").text

    assert 'id="app-nav"' in html
    assert 'id="btn-demo"' in html
    assert 'id="btn-compare-report"' in html
    assert 'id="btn-print"' in html
    assert 'id="status-bar"' in html
    assert 'id="sensitivity_tables"' in html
    assert 'id="twin_summary"' in html
    assert 'id="decisions_empty"' in html
    assert "Comparación de escenarios" in html
    assert "Imprimir" in html
    assert "Crear empresa" in html
    assert "Fraunces" in css or "fraunces" in css.lower()
    assert "DM Sans" in css or "dm-sans" in css.lower() or "DM+Sans" in css
    assert "#0b6e6b" in css.lower()
    assert "@media print" in css

    assert "fillSensitivityTable" in js
    assert "validatePackInputs" in js
    assert "printReport" in js
    assert "showStatus" in js
    assert "METRIC_LABELS" in js
    assert "Valor creado (VAN)" in js
    assert "Math." not in js
    assert "average(" not in js.lower()


def test_ui_p8_stable_ids(client: TestClient) -> None:
    html = client.get("/").text
    for eid in (
        "btn-run",
        "btn-compare",
        "btn-sensitivity",
        "btn-register-decision",
        "metrics",
        "compare",
        "sensitivity_out",
        "sec-report",
        "sec-twin-loop",
        "sec-import",
        "pack_fields",
    ):
        assert f'id="{eid}"' in html, eid
