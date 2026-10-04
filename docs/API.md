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

### `GET /packs`

Lista los `pack_id` MVP (`new_site`, `financing`, `asset_purchase`, `hiring`, `generic_investment`, `liquidity_plan`).

---

### `POST /companies/{company_id}/packs/{pack_id}/run`

Ejecuta **cualquier** pack MVP sobre el twin current (P1):

1. validate + build (en memoria; **no** muta ModelVersion)
2. persiste `Scenario` + `CalculationRun`
3. calcula con el motor

Body:

```json
{
  "inputs": { "...": "campos del pack (DECISION_PACKS)" },
  "variant": "base"
}
```

`variant`: `base` | `conservative` | `adverse`  
`pack_id`: uno de `GET /packs` (incl. `new_site`).

Decimales en respuesta: **strings** (MODELO §12).

Respuesta (campos clave):

```json
{
  "company_id": "...",
  "pack_id": "new_site",
  "model_version_id": "...",
  "scenario_id": "...",
  "calculation_run_id": "...",
  "variant": "base",
  "engine_version": "0.1.0",
  "inputs_hash": "...",
  "result_hash": "...",
  "actual_keys": ["sales_monthly", "..."],
  "investment_metrics": { "npv": "123.45", "irr_annual": null, "payback_simple": 12, "...": "..." },
  "financing_need": { "min_cash": "...", "max_shortfall_vs_policy": "...", "...": "..." },
  "policy_checks": [],
  "warnings": [],
  "results": { "...": "CalculationResult serializado" }
}
```

Errores: pack desconocido / funding / validación → `400`; company sin snapshot → `400`; company inexistente → `404`.

Compat: `POST .../packs/new_site/run` es el mismo contrato (ruta parametrizada).

UI (P3): el Decision Studio puede lanzar **tres** runs (`base` / `conservative` / `adverse`) con los mismos `inputs` y mostrar la tabla de comparación con campos 1:1 de cada respuesta (sin promedios en el cliente).

---

### `GET /calculation-runs/{run_id}`

Recupera `CalculationRun` persistido (`calculation_input` + `results` con Decimals string).

---

## Twin Loop (F7)

### `GET /companies/{company_id}/decisions`

Lista decisiones de la empresa (P4), orden `number` DESC. Campos resumen + `actual_results_count` (sin `frozen_projection`).

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

## Import twin CSV (P5)

### `GET /templates/twin_snapshot_template.csv`

Descarga la plantilla documentada (`api/templates/`).

### `POST /companies/{company_id}/imports/twin-csv`

`multipart/form-data`:

- `file`: CSV UTF-8 (secciones `# SECTION …`)
- `label` (opcional): etiqueta de ModelVersion

Flujo: parse → `snapshot_from_dict` → `put_current_snapshot` (nueva MV current).

Errores de formato/schema → `400` `{ "code": "csv_format"|"snapshot_invalid", "message": "..." }`.

README columnas: `api/templates/README.md`.

---

## Sensibilidad (P6)

### `POST /companies/{company_id}/packs/{pack_id}/sensitivity`

Orquesta `financetwin_engine.analytics.sensitivity.run_analysis`:

1. Lee twin current (**no** muta ModelVersion)
2. Para cada bloque: clona inputs → `pack.build` → `calculate()`
3. Devuelve métricas como **strings** Decimal

Body:

```json
{
  "inputs": { "...": "inputs del pack" },
  "variant": "base",
  "include": ["direct", "inverse", "stress"]
}
```

MVP: pack `new_site` (DECISION_PACKS §5.5). Otros packs sin `analysis_plan` → `400`.

Respuesta clave: `direct` (±10% por variable), `inverse` (umbrales VAN=0 / min_cash=policy), `stress` (sales −15/−30, open +2/+4m, rate +200 bp).

---

## Producto uso C + UX (P9–P15)

### `GET /companies`

Lista empresas locales (sin auth): `{ "companies": [ { id, name, country, currency, created_at } ] }`.

### `GET /companies/{company_id}/twin-quality`

Checklist factual del twin current (`checks`, `ready_for_packs`, `summary`). También en `GET .../snapshot` como campo `quality`.

### `POST /companies/{company_id}/reports/executive`

Body: `{ "run": CalculationRun, "compare": { base, conservative, adverse } | null, "company_name": "..." }`.

Devuelve **HTML** descargable (`Content-Disposition: attachment`). Solo pinta campos del body; **no recalcula**.

---

## Notas

- BD: `FINANCETWIN_DB` o `api/data/financetwin.sqlite`
- Sin autenticación (MVP local; auth diferida)
- Dependencia form upload: `python-multipart`
- UI Decision Studio (P2–P15): `GET /` + estáticos en `/static/*`
- IA (F9) → diferida
