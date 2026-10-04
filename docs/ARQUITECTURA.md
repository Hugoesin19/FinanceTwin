# Arquitectura — Finance Twin (lo implementado)

Fecha: 2026-10-04  
Alcance: F0–F8 + P1–P15 (uso C + UX shell + flujo humano). Sin auth/deploy/F9.

---

## Capas reales

```
Browser (onboarding · Home gated · wizards · resultado narrado — P15)
    │  same-origin HTTP
    ▼
FastAPI  api/financetwin_api
    │  SQLite + packs + Twin Loop + twin_quality + report_html
    ▼
financetwin_engine  (Decimal, determinista + analytics)
```

| Capa | Ruta | Rol |
|---|---|---|
| Motor | `engine/financetwin_engine/` | Cálculo L0; única fuente de cifras |
| Mapper / packs | `engine/.../mapper`, `packs` | Snapshot → CalculationInput; Decision Packs |
| API + BD | `api/financetwin_api/` | Persistencia MODELO mínima + endpoints |
| UI | `api/financetwin_api/static/` | Decision Studio (HTML/JS; Atlantic Ledger; P15 flujo humano) |
| Validación | `validation/` | Campaña F8 Plan B + informe §10 |

## Decisiones de stack (MVP local, €0)

1. **SQLite** en lugar de Postgres — suficiente para TFG local (F5).
2. **UI estática servida por FastAPI** (`/` + `/static`) — no hay app Next.js aún; PRODUCTO.md cita Next.js como objetivo de producto, no como requisito de F6/P8.
3. **Sin auth** — MVP single-user local.
4. **Decimales como string** en JSON (MODELO §12).

## Regla anti-alucinación de números

- El motor calcula.
- La API serializa (`to_jsonable`).
- La UI **solo pinta** campos del `CalculationRun` / respuesta de run (p. ej. `irr_annual`, no aliases inventados).
- Al recargar, la UI restaura `company_id` (localStorage) y **hidrata** el twin desde `GET .../snapshot` (si la empresa ya no existe, limpia sesión).
- P7/P8: demo, compare y sensibilidad no inventan cifras; llaman a los mismos endpoints.
- P15: onboarding Crear/Demo, jobs gated, demo banner, Resultado en nav, formato es-ES display-only, Twin Loop humano.

## Cómo arrancar

```powershell
cd api
python -m pip install -e ../engine -e ".[dev]"
$env:FINANCETWIN_DB = ".\data\financetwin.sqlite"
uvicorn financetwin_api.main:app --reload --port 8000
```

Abrir http://127.0.0.1:8000/ → Home (3 jobs) o «Cargar demo» → Decidir/Liquidez → resultado hero.  
API genérica P1: `POST /companies/{id}/packs/{pack_id}/run` + `GET /packs`.

Spec API: [`API.md`](API.md). Plan núcleo: [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md). Producto: [`PLAN_PRODUCTO.md`](PLAN_PRODUCTO.md).
