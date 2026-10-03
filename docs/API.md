# API — Finance Twin (implementado)

Versión: `0.1` (F5)  
Alcance: **solo endpoints existentes**. Sin auth.

Base local: FastAPI + SQLite.

---

## Endpoints

### `GET /health`

Respuesta:

```json
{ "status": "ok", "engine_version": "0.1.0" }
```

---

### `POST /companies`

Crea empresa.

Body:

```json
{ "name": "Demo SL", "country": "ES", "currency": "EUR" }
```

Respuesta: `{ id, name, country, currency, created_at }`

---

### `PUT /companies/{company_id}/snapshot`

Guarda snapshot como **nueva** `ModelVersion` current (no muta versiones referenciadas).

Body:

```json
{
  "snapshot": { "schema_version": "1.0", "company": { "...": "..." }, "...": "..." },
  "label": "optional"
}
```

`snapshot` debe pasar validación `CompanyTwinSnapshot` (`schema_version=1.0`).

Respuesta: `{ company_id, model_version_id, is_current: true }`

---

### `GET /companies/{company_id}/snapshot`

Devuelve snapshot current + `model_version_id`.

Errores:
- `404` `company not found`
- `404` `no current snapshot`

---

### `POST /companies/{company_id}/packs/new_site/run`

Ejecuta pack `new_site` sobre el twin current:

1. validate + build (en memoria; **no** muta ModelVersion)
2. persiste `Scenario` + `CalculationRun`
3. calcula con el motor

Body:

```json
{
  "inputs": { "site_name": "...", "open_year_month": "2027-01", "...": "..." },
  "variant": "base"
}
```

`variant`: `base` | `conservative` | `adverse`

Decimales en respuesta: **strings** (MODELO §12).

Respuesta (campos clave):

```json
{
  "company_id": "...",
  "model_version_id": "...",
  "scenario_id": "...",
  "calculation_run_id": "...",
  "variant": "base",
  "engine_version": "0.1.0",
  "inputs_hash": "...",
  "result_hash": "...",
  "investment_metrics": { "npv": "123.45", "irr_annual": null, "payback_simple": 12, "...": "..." },
  "financing_need": { "min_cash": "...", "max_shortfall_vs_policy": "...", "...": "..." },
  "policy_checks": [],
  "warnings": [],
  "results": { "...": "CalculationResult serializado" }
}
```

Errores de funding / validación → `400`.

---

### `GET /calculation-runs/{run_id}`

Recupera `CalculationRun` persistido (`calculation_input` + `results` con Decimals string).

---

## Twin Loop (F7)

### `POST /companies/{company_id}/decisions`

Registra una `Decision` a partir de un `calculation_run_id` (no muta el twin).

Body (mínimo):

```json
{
  "title": "Abrir Tienda Alicante",
  "decision_pack_id": "new_site",
  "decision_date": "2027-01-15",
  "calculation_run_id": "...",
  "status": "approved",
  "rationale": "..."
}
```

`status` típicos: `draft` | `approved` | `executed` (… según MODELO §8.1).  
Crea hitos por defecto (+3/+6/+12 meses). Decimals en `forecast_metrics` como strings.

### `GET /decisions/{decision_id}`

Decision + milestones + actual_results.

### `POST /decisions/{decision_id}/status`

Transición de estado (`{"status": "executed"}`). Reglas MODELO §8.1.

### `POST /decisions/{decision_id}/actuals`

Solo si `status=executed`. Calcula `deviation_pct = (forecast-actual)/forecast` y actualiza `BiasProfile`.

```json
{
  "period_year_month": "2027-06",
  "items": [
    {
      "variable_key": "sales_monthly",
      "forecast_value": "40000",
      "actual_value": "32800",
      "source": "manual"
    }
  ]
}
```

### `GET /companies/{company_id}/packs/{pack_id}/bias-profiles`

Lista perfiles de sesgo del pack.

### `POST /companies/{company_id}/packs/{pack_id}/calibration/preview`

Ofrece inputs calibrados **solo** si alguna key tiene `n_observations >= 3` (§2.6), donde `n` = nº de **decisiones** executed con ActualResult (no filas/periodos):

`calibrated = user_value * (1 - median_bias)`

```json
{ "inputs": { "sales_run_rate": "40000", "...": "..." } }
```

Respuesta: `{ offered, calibrated_inputs|null, applied, skipped, profiles }`.

---

## Notas

- BD: `FINANCETWIN_DB` o `api/data/financetwin.sqlite`
- Sin autenticación (MVP local)
- UI mínima (F6): `GET /` + estáticos en `/static/*` (Decision Studio)
- Otros packs / Next.js / IA → fases posteriores
