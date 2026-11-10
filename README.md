# Finance Twin

Financial Decision Platform for SMEs.

Finance Twin builds a financial twin of a company so managers can simulate major decisions before executing them — and learn from forecast vs reality over time.

> **Before you spend €300,000, try it here.**

## Product thesis

- Sits **on top of** accounting / ERP / advisory tools — does not replace them
- **Decision Studio** is the core: what-if scenarios for capital and financing decisions
- **Twin Loop**: forecast → decision → reality → deviation → calibration
- **AI interprets. The financial engine calculates.**

## Documentación

**Al programar producto usable:** [`docs/PLAN_PRODUCTO.md`](docs/PLAN_PRODUCTO.md) (P1–P8; F9 diferida).  
**Reglas + fundación F0–F8:** [`docs/PLAN_IMPLEMENTACION.md`](docs/PLAN_IMPLEMENTACION.md).

- [`docs/DOCUMENTACION.md`](docs/DOCUMENTACION.md) — inventario
- [`docs/PLAN_PRODUCTO.md`](docs/PLAN_PRODUCTO.md) — **plan producto (activo)**
- [`docs/PLAN_IMPLEMENTACION.md`](docs/PLAN_IMPLEMENTACION.md) — plan fundación F0–F8
- [`docs/PRODUCTO.md`](docs/PRODUCTO.md) — producto
- [`docs/MOTOR_FINANCIERO.md`](docs/MOTOR_FINANCIERO.md) — motor
- [`docs/MODELO_DATOS.md`](docs/MODELO_DATOS.md) — datos
- [`docs/DECISION_PACKS.md`](docs/DECISION_PACKS.md) — packs
- [`docs/VALIDACION.md`](docs/VALIDACION.md) — validación

## Status

Producto usable: Resultado con trade-off/runway/DSCR/scorecard, liquidez con presets, import SABI/Excel, tornado + Monte Carlo, Twin Loop en lenguaje claro, demo one-click (`POST /demo/bootstrap`), cuentas gratis con `X-Org-Token`.

## Probar en local / Docker

```bash
pip install -e engine -e api
uvicorn financetwin_api.main:app --app-dir api --reload --port 8000
```

```bash
docker compose up --build
# http://localhost:8000  ·  health: GET /health  ·  demo: POST /demo/bootstrap
```

Deploy HTTPS: `Dockerfile` + `fly.toml` (volumen `/data` para SQLite). Signup: `POST /auth/signup`.

## Repository

Private — Hugoesin19/FinanceTwin
