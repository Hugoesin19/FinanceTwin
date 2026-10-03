# Arquitectura — Finance Twin (lo implementado)

Fecha: 2026-10-03  
Alcance: F0–F6 (sin inventar capas futuras).

---

## Capas reales

```
Browser (UI mínima F6)
    │  same-origin HTTP
    ▼
FastAPI  api/financetwin_api
    │  SQLite + packs + mapper + Twin Loop (F7)
    ▼
financetwin_engine  (Decimal, determinista + analytics/bias)
```

| Capa | Ruta | Rol |
|---|---|---|
| Motor | `engine/financetwin_engine/` | Cálculo L0; única fuente de cifras |
| Mapper / packs | `engine/.../mapper`, `packs` | Snapshot → CalculationInput; Decision Packs |
| API + BD | `api/financetwin_api/` | Persistencia MODELO mínima + endpoints |
| UI | `api/financetwin_api/static/` | Decision Studio mínimo (HTML/JS) |

## Decisiones de stack (MVP local, €0)

1. **SQLite** en lugar de Postgres — suficiente para TFG local (F5).
2. **UI estática servida por FastAPI** (`/` + `/static`) — no hay app Next.js aún; PRODUCTO.md cita Next.js como objetivo de producto, no como requisito de F6.
3. **Sin auth** — MVP single-user local.
4. **Decimales como string** en JSON (MODELO §12).

## Regla anti-alucinación de números

- El motor calcula.
- La API serializa (`to_jsonable`).
- La UI **solo pinta** campos del `CalculationRun` / respuesta de run (p. ej. `irr_annual`, no aliases inventados).
- Al recargar, la UI restaura `company_id` (localStorage) y **hidrata** el twin desde `GET .../snapshot` (si la empresa ya no existe, limpia sesión).

## Cómo arrancar

```powershell
cd api
python -m pip install -e ../engine -e ".[dev]"
$env:FINANCETWIN_DB = ".\data\financetwin.sqlite"
uvicorn financetwin_api.main:app --reload --port 8000
```

Abrir http://127.0.0.1:8000/ → crear empresa → twin → calcular `new_site`.

Spec API: [`API.md`](API.md). Plan: [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md).
