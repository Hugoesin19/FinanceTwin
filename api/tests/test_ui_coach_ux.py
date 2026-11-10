"""UX flujo guiado: gate de empresa + datos + coach + sidebar."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from financetwin_api.main import create_app


@pytest.fixture()
def client(tmp_path: Path):
    application = create_app(str(tmp_path / "coach.sqlite"))
    with TestClient(application) as c:
        yield c


def test_coach_bar_and_company_gate(client: TestClient) -> None:
    html = client.get("/").text
    js = client.get("/static/app.js").text
    css = client.get("/static/styles.css").text

    assert 'id="coach_bar"' in html
    assert 'id="coach_text"' in html
    assert 'id="coach_cta"' in html
    # Inicio = solo empresas
    assert "Tus empresas" in html
    assert 'id="home_company_name"' in html
    assert 'id="btn-create-home"' in html
    assert 'id="btn-demo-home"' in html
    assert 'id="sec-companies-mgmt"' in html
    assert 'id="companies-mgmt-table"' in html
    # Intents de datos viven en Datos / twin (tras elegir empresa)
    assert 'id="home-intent-demo"' in html
    assert 'id="home-intent-sabi"' in html
    assert 'id="home-intent-manual"' in html
    assert 'id="home-intent"' in html
    assert 'id="sabi_flow"' in html
    assert 'id="sabi-step-1"' in html
    assert 'id="data_path_chooser"' in html
    assert "Excel propio" in html or "plantilla CSV" in html or "Plantilla CSV" in html
    assert "Análisis avanzado" in html
    assert 'id="actuals_howto"' in html
    assert "Previsto (simulación)" in html

    assert "createCompanyShell" in js
    assert "useCompany" in js
    assert "enterCompanyWorkspace" in js
    assert "renderCoach" in js
    assert "deriveCoachState" in js
    assert "openTwinForIntent" in js
    assert "startIntentSabi" in js
    assert "showDataPath" in js
    assert "updateSidebarProgressive" in js
    assert "updateSidebarCompanyGate" in js
    assert "applyLiquidityPreset" not in js

    assert ".coach-bar" in css
    assert ".intent-grid" in css
    assert ".sabi-steps" in css


def test_sidebar_human_labels(client: TestClient) -> None:
    html = client.get("/").text
    assert "Datos / twin" in html or "Datos del twin" in html
    assert "Simular decisión" in html or ">Decisión<" in html
    assert 'id="nav-report"' in html
    assert 'id="nav-followup"' in html
    assert "nav-late" in html


def test_result_primary_cta_not_flood(client: TestClient) -> None:
    html = client.get("/").text
    assert 'id="btn-goto-register"' in html
    assert 'id="result-more-actions"' in html
    # Análisis avanzado cerrado por defecto (sin open en el details)
    assert 'id="result-more-actions" open' not in html
