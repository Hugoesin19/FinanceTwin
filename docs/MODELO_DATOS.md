# MODELO DE DATOS — Especificación

**Finance Twin Data Model**  
Versión de spec: `1.1` *(revisión post-auditoría)*  
Estado: lista para implementación (MVP)  
Referencias: [`PRODUCTO.md`](PRODUCTO.md) §10, §14, §21 · [`MOTOR_FINANCIERO.md`](MOTOR_FINANCIERO.md) §4–5

---

## 0. Propósito

Este documento define **qué datos existen, con qué forma, qué relaciones y qué reglas**.

- Si un campo no está aquí, **no se inventa** en código/API/BD.
- El motor **no habla con la BD**: recibe un `CalculationInput` ya materializado.
- Persistencia (Postgres/SQLite) y DTOs de API deben mapear a este modelo.
- Ante conflicto con `MOTOR_FINANCIERO.md` en campos de cálculo, **gana el motor** y se actualiza este doc.

Constraint: **presupuesto 0 €** en desarrollo → PostgreSQL local o SQLite aceptable al inicio; mismos conceptos lógicos.

---

## 1. Principios

| ID | Principio | Implicación |
|---|---|---|
| D1 | **Dos capas** | Dominio persistente (empresa, versiones, decisiones) ≠ snapshot de cálculo (`CalculationInput`) |
| D2 | **Tiempo dual** | En BD: fechas `YYYY-MM-DD` / `YYYY-MM`. En motor: índices `t = 0..H-1` |
| D3 | **Dinero Decimal** | Nunca float en campos monetarios o porcentajes financieros |
| D4 | **IDs estables** | UUID (o ULID) como PK; IDs legibles solo como `number` de decisión |
| D5 | **Versionado explícito** | El modelo vivo se congela en `ModelVersion` / escenarios |
| D6 | **Linaje** | Todo dato relevante tiene origen y, si aplica, confianza |
| D7 | **Soft rules** | Validación dura en API/motor; warnings cuando la calidad es baja |
| D8 | **Multi-tenant** | Toda fila de negocio lleva `company_id` (salvo users globales) |

---

## 2. Diagrama lógico (MVP)

```text
User ──< CompanyUser >── Company
                           │
           ┌───────────────┼───────────────────────────────┐
           ▼               ▼                               ▼
     BusinessUnit    CompanyPolicy / FiscalConfig     DataSource
           │               │
           ▼               ▼
     ModelVersion ◄── entities del twin (streams, costs, …)
           │
           ▼
        Scenario ──< CalculationRun
           │
           ▼
        Decision ──< DecisionMilestone
           │         ActualResult
           ▼
        BiasProfile
```

---

## 3. Tipos base

| Tipo lógico | Representación | Notas |
|---|---|---|
| `ID` | UUID string | PK |
| `Money` | Decimal(20,2) o Decimal genérico + scale 2 al persistir | |
| `Rate` | Decimal (fracción: `0.21` = 21 %) | No guardar `21` como por ciento en núcleo |
| `Count` | int ≥ 0 | |
| `MonthIndex` | int ≥ 0 | Solo en snapshots de motor / resultados |
| `YearMonth` | `YYYY-MM` | Preferido para series |
| `Date` | `YYYY-MM-DD` | |
| `Timestamp` | UTC ISO-8601 | |
| `JSON` | objeto/array | seasonality, overrides, snapshots |
| `Text` | string | |
| `Enum` | string cerrado | ver §4 |

### 3.1 Enums cerrados (MVP)

```text
UserRole:                 owner | finance | viewer | advisor
Confidence:               high | medium | low
DataOrigin:               historical | user | sector | calibrated | imported | calculated
RevenueType:              recurring | transactional | project
CostNature:               fixed | variable_pct_revenue
LoanRateType:             fixed
AmortizationSystem:       french | linear | bullet
GraceType:                capital | total | none
DepreciationMethod:       straight_line | declining_simple
AcquisitionFunding:       cash | loan | mixed
VatSettlement:            monthly | quarterly
CorpTaxPaymentMode:       none | annual_end | quarterly_approx
ScenarioType:             base | optimistic | conservative | adverse | custom | calibrated
DecisionStatus:           draft | approved | rejected | deferred | executed | cancelled
MilestoneStatus:          pending | done | skipped
ImportStatus:             pending | running | completed | failed
CalculationRunStatus:     completed | failed
DataSourceStatus:         active | inactive | error
BiasDirection:            overestimate | underestimate | mixed
OneOffKind:               equity_injection | dividend | other_in | other_out | capex
AssumptionValueType:      money | rate | count | text | bool
DecisionPackId:           new_site | financing | asset_purchase | hiring | generic_investment | liquidity_plan
AccountTargetCategory:    revenue | cogs | other_opex | payroll | capex | loan_drawdown | loan_repayment | interest | tax_vat | tax_corp | cash | equity | other | ignore
```

*(Los packs se detallan en `DECISION_PACKS.md`; aquí solo el id canónico.)*

**Nota sobre `Rate` vs múltiplos:**  
`Rate` = fracción (`0.25` = 25 %).  
Ratios tipo Deuda/EBITDA (`3.0`) **no** son `Rate`: usar `Decimal` adimensional.

---

## 4. Entidades de organización

### 4.1 User

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| email | Text | sí | único |
| name | Text | sí | |
| created_at | Timestamp | sí | |
| is_active | bool | sí | default true |

### 4.2 Company

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| name | Text | sí | |
| sector | Text | no | libre / catálogo simple |
| country | Text | sí | default `ES` |
| currency | Text | sí | default `EUR` (única en MVP) |
| fiscal_year_start_month | int 1–12 | sí | default 1 |
| timezone | Text | sí | default `Europe/Madrid` |
| created_at | Timestamp | sí | |
| archived_at | Timestamp | no | |

**Importante — `opening_cash` y plazos de pago NO viven solo en `Company` “suelta”:**  
La fuente de verdad versionada está en `ModelVersion.snapshot.company` (`opening_cash`, `default_purchase_payment_days`, `currency`).  
La fila `Company` guarda metadatos estables (nombre, sector, país…). Si se cachea `opening_cash` en `Company` por comodidad UI, es **denormalización** y debe sincronizarse al editar el snapshot current.

### 4.3 CompanyUser

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| company_id | ID | sí | FK |
| user_id | ID | sí | FK |
| role | UserRole | sí | |
| created_at | Timestamp | sí | |

PK compuesta `(company_id, user_id)`.

### 4.4 FiscalConfig *(1:1 con Company, versionable vía ModelVersion snapshot)*

En persistencia puede vivir dentro del snapshot del modelo; lógicamente:

| Campo | Tipo | Req | Default |
|---|---|---|---|
| vat_rate | Rate | sí | 0.21 |
| vat_settlement | VatSettlement | sí | quarterly |
| vat_payment_lag_months | Count | sí | 1 |
| corp_tax_rate | Rate | sí | 0.25 |
| corp_tax_payment_mode | CorpTaxPaymentMode | sí | quarterly_approx |

### 4.5 CompanyPolicy *(guardrails)*

| Campo | Tipo | Req | Default sugerido |
|---|---|---|---|
| company_id | ID | sí | |
| min_cash | Money | sí | 0 |
| max_debt_ebitda | Decimal | no | 3.0 (múltiplo, no Rate) |
| min_dscr | Decimal | no | 1.3 |
| max_payback_months | Count | no | 60 |
| min_irr | Rate | no | 0.12 |
| max_capex_pct_cash | Rate | no | null |

Una fila “live” por empresa.  
Al crear/actualizar `ModelVersion`, se **copia** al snapshot. Los escenarios históricos usan la policy del snapshot, no la live.

---

## 5. Modelo twin (versión)

### 5.1 ModelVersion

Congela el estado del twin en un instante.

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| company_id | ID | sí | |
| parent_id | ID | no | versión anterior |
| label | Text | no | ej. `v47`, `pre-tienda-alicante` |
| changelog | Text | no | |
| is_current | bool | sí | solo una `true` por company |
| snapshot | JSON | sí | **copia completa** de entidades twin + fiscal + policies relevantes |
| created_by | ID | sí | user |
| created_at | Timestamp | sí | |

**Regla:** las entidades “vivas” se editan sobre la versión current; al calcular un escenario aprobado / decisión, se referencia un `model_version_id` inmutable.

### 5.1.1 Estrategia de persistencia v0.1 (única, no ambigua)

**Decisión normativa MVP:**

1. `ModelVersion.snapshot` (JSON validado por schema) es la **única fuente de verdad** del twin en cada versión.
2. No hay tablas normalizadas paralelas de `revenue_stream` / `loan` / etc. en v0.1.
3. Edición = clonar snapshot current → mutar → guardar nueva `ModelVersion` (o reemplazar current si aún no hay cálculos/decisiones colgando; ver regla abajo).
4. Regla de mutación del current:
   - Si **ningún** `Scenario` / `Decision` / `CalculationRun` referencia ese `model_version_id` → se puede actualizar el snapshot in-place (mismo id) **o** versionar; preferible versionar siempre si es barato.
   - Si ya hay referencias → **obligatorio** crear nueva `ModelVersion` y marcar `is_current` en la nueva.

Esto evita el dilema “tablas vs JSON” y encaja con presupuesto 0 / velocidad de TFG.  
Si más adelante hace falta query SQL por línea de ingreso, se introduce proyección/tablas derivadas sin cambiar el schema lógico del snapshot.

### 5.2 Snapshot schema (contenido)

```text
CompanyTwinSnapshot
├── schema_version: "1.0"
├── company:
│     currency
│     opening_cash
│     default_purchase_payment_days
├── fiscal: FiscalConfig
├── policies: { min_cash, max_debt_ebitda, min_dscr, max_payback_months, min_irr, max_capex_pct_cash }
├── business_units: BusinessUnit[]
├── revenue_streams: RevenueStream[]
├── cost_items: CostItem[]
├── payroll: PayrollLine[]
├── loans: Loan[]
├── assets: Asset[]
├── investments: Investment[]
├── one_off_cash_events: OneOffCashEvent[]
└── assumptions: Assumption[]
```

`Company.id`, `name`, etc. no hace falta duplicarlos dentro del snapshot (viven en tabla `Company`); el snapshot solo lleva lo que el motor necesita + twin económico.

---

## 6. Entidades del twin

Convención temporal en entidades:

- Persistencia / UX: `start_year_month`, `end_year_month` (`YYYY-MM`)
- Al construir `CalculationInput`: convertir a `start_t`, `end_t` con `scenario.anchor_year_month` como `t=0`

### 6.1 BusinessUnit

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| name | Text | sí | ej. `Tienda Valencia` |
| unit_type | Text | no | store, channel, line… |
| start_year_month | YearMonth | no | |
| is_active | bool | sí | default true |

### 6.2 RevenueStream

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| name | Text | sí | |
| revenue_type | RevenueType | sí | |
| business_unit_id | ID | no | |
| start_year_month | YearMonth | sí | |
| end_year_month | YearMonth | no | inclusive |
| base_monthly_revenue | Money | sí | base imponible en régimen |
| ramp | Rate[] | no | factores desde el mes start; default implícito 1 |
| seasonality | Rate[12] | no | índice 0=enero … 11=diciembre; default 1 |
| growth_annual | Rate | sí | default 0 |
| gross_margin_pct | Rate | sí | 0..1 |
| collection_days | Count | sí | |
| origin | DataOrigin | sí | |
| confidence | Confidence | sí | |
| notes | Text | no | |

**Invariantes:**  
`0 ≤ gross_margin_pct ≤ 1` · `base_monthly_revenue ≥ 0` · si `end` existe → `end ≥ start`

### 6.3 CostItem

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| name | Text | sí | |
| nature | CostNature | sí | |
| business_unit_id | ID | no | |
| start_year_month | YearMonth | sí | |
| end_year_month | YearMonth | no | |
| amount_monthly | Money | cond | obligatorio si `fixed` |
| pct_of_revenue | Rate | cond | obligatorio si `variable_pct_revenue` |
| payment_days | Count | sí | |
| growth_annual | Rate | sí | default 0 |
| seasonality | Rate[12] | no | |
| is_vatable | bool | sí | default true |
| origin | DataOrigin | sí | |
| confidence | Confidence | sí | |
| notes | Text | no | |

### 6.4 PayrollLine

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| role_name | Text | sí | |
| headcount | Count | sí | ≥ 1 |
| monthly_employer_cost | Money | sí | coste empresa por persona |
| business_unit_id | ID | no | |
| start_year_month | YearMonth | sí | |
| end_year_month | YearMonth | no | |
| payment_days | Count | sí | default 0 |
| origin | DataOrigin | sí | |
| confidence | Confidence | sí | |

### 6.5 Loan

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| name | Text | sí | |
| lender | Text | no | |
| principal | Money | sí | > 0 |
| annual_interest_rate | Rate | sí | TIN nominal anual (ver motor) |
| rate_type | LoanRateType | sí | `fixed` |
| term_months | Count | sí | ≥ 1 (meses de amortización tras carencia) |
| amortization_system | AmortizationSystem | sí | |
| grace_months | Count | sí | default 0 |
| grace_type | GraceType | sí | `none` si grace_months=0 |
| disbursement_year_month | YearMonth | sí | |
| origination_fee | Money | sí | default 0 |
| origin | DataOrigin | sí | |
| confidence | Confidence | sí | |
| notes | Text | no | |

**Invariantes:**  
si `grace_months=0` → `grace_type=none` · si `grace_months>0` → `grace_type ∈ {capital, total}`

**Mapper → motor:**  
El motor (`MOTOR_FINANCIERO`) tipa `grace_type` como `capital | total`.  
Si `grace_type=none` / `grace_months=0`, **no enviar** campo de carencia al schedule (o enviar `grace_months=0` y omitir grace_type). Nunca enviar `none` al motor.

### 6.6 Asset

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| name | Text | sí | |
| asset_type | Text | no | vehicle, equipment, premises… |
| acquisition_cost | Money | sí | base; IVA aparte vía flags fiscales |
| acquisition_year_month | YearMonth | sí | |
| useful_life_months | Count | sí | ≥ 1 |
| residual_value | Money | sí | default 0; ≤ cost |
| depreciation_method | DepreciationMethod | sí | |
| acquisition_funding | AcquisitionFunding | sí | |
| funding_loan_id | ID | cond | si funding = loan o mixed |
| investment_id | ID | no | si ligado a proyecto (anti doble CAPEX) |
| origin | DataOrigin | sí | |
| confidence | Confidence | sí | |

### 6.7 Investment

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| name | Text | sí | |
| decision_pack_id | DecisionPackId | no | si nació de un pack |
| capex_schedule | CapexPoint[] | sí | ver abajo |
| linked_revenue_stream_ids | ID[] | sí | puede vacío |
| linked_cost_item_ids | ID[] | sí | |
| linked_payroll_ids | ID[] | sí | |
| linked_loan_ids | ID[] | sí | |
| linked_asset_ids | ID[] | sí | |
| own_funds_year_month | YearMonth | no | aportación recursos propios |
| own_funds_amount | Money | no | |
| analysis_start_year_month | YearMonth | sí | |
| analysis_horizon_months | Count | sí | |
| discount_rate_annual | Rate | no | si null, usa el del escenario/cálculo |
| notes | Text | no | |

**CapexPoint**

| Campo | Tipo | Req |
|---|---|---|
| year_month | YearMonth | sí |
| amount | Money | sí |
| includes_vat | bool | sí | default false (amount = base) |
| label | Text | no |

**Regla anti doble CAPEX:** si un `Asset.investment_id` apunta aquí, el desembolso de ese asset **no** se suma otra vez fuera de `capex_schedule`.

**Invariante bidireccional:**  
si `asset.investment_id = I`, entonces `asset.id ∈ investment[I].linked_asset_ids`, y viceversa para cada id listado.

### 6.7.1 Recursos propios del proyecto (sin dobles caminos)

Si el proyecto aporta capital propio:

- Preferente: `Investment.own_funds_year_month` + `own_funds_amount`
- El mapper genera **un** `OneOffCashEvent` implícito `equity_injection` al construir `CalculationInput`
- **No** crear a mano un `OneOffCashEvent` duplicado por el mismo concepto

Si se usa `OneOffCashEvent` suelto de equity, no rellenar `own_funds_*` del mismo importe/mes.

### 6.8 OneOffCashEvent

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| year_month | YearMonth | sí | |
| amount | Money | sí | siempre ≥ 0; el signo lo da `kind` |
| kind | OneOffKind | sí | |
| label | Text | no | |

### 6.9 Assumption

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| key | Text | sí | único por company/version, ej. `growth.sales` |
| name | Text | sí | legible |
| value | Decimal/Text | sí | tipar con `value_type` |
| value_type | AssumptionValueType | sí | |
| unit | Text | no | |
| origin | DataOrigin | sí | |
| confidence | Confidence | sí | |
| min_plausible | Decimal | no | |
| max_plausible | Decimal | no | |
| justification | Text | no | |

Las Assumptions alimentan defaults de packs y sensibilidad; el motor puede recibirlas ya resueltas en `assumptions_resolved`.

---

## 7. Escenarios y cálculos

### 7.1 Scenario

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| company_id | ID | sí | |
| name | Text | sí | |
| scenario_type | ScenarioType | sí | |
| parent_scenario_id | ID | no | |
| base_model_version_id | ID | sí | snapshot de partida |
| anchor_year_month | YearMonth | sí | mes = `t=0` |
| horizon_months | Count | sí | H |
| discount_rate_annual | Rate | sí | |
| auto_finance_deficits | bool | sí | default false |
| auto_finance_config | JSON | cond | obligatorio si `auto_finance_deficits=true` |
| overrides | JSON | sí | lista de overrides (§7.2) |
| locked | bool | sí | default false |
| created_by | ID | sí | |
| created_at | Timestamp | sí | |

**`auto_finance_config` (cuando aplica):**

```text
{
  "annual_interest_rate": 0.06,
  "term_months": 12,
  "amortization_system": "french",
  "cushion_amount": 0,           # Money extra sobre el shortfall
  "max_iterations": 5
}
```

**Regla:** si `locked=true`, no se editan overrides (solo clonar).

### 7.2 Override / BuildOp (forma canónica)

Alineado con `DECISION_PACKS.md` §2.4.

```text
BuildOp
├── op: add_entity | set_field   # si falta op => set_field
├── entity_type     # revenue_streams | cost_items | payroll | loans | assets | investments | company | fiscal | policies | assumptions | one_off_cash_events | business_units
├── entity_id       # obligatorio salvo set_field sobre company|fiscal|policies
├── field?          # set_field
├── value?          # set_field (Decimal como string si money/rate)
├── payload?        # add_entity: entidad completa
└── justification?
```

Orden: todos los `add_entity` (en orden), luego `set_field` (en orden).

Al materializar:

```text
effective_snapshot = apply_build_ops(base_model_version.snapshot, overrides)
CalculationInput = to_calculation_input(effective_snapshot, scenario)
```

### 7.3 CalculationRun

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| scenario_id | ID | sí | |
| company_id | ID | sí | denormalizado |
| engine_version | Text | sí | semver |
| model_version_id | ID | sí | |
| inputs_hash | Text | sí | |
| calculation_input | JSON | sí | input exacto enviado al motor |
| results | JSON | sí | `CalculationResult` serializado |
| trace | JSON | no | puede ir dentro de results |
| random_seed | Text | no | null en v0.1 (determinista puro) |
| status | CalculationRunStatus | sí | |
| error_message | Text | no | |
| computed_by | ID | no | |
| computed_at | Timestamp | sí | |

**Invariante:** mismo `inputs_hash` + `engine_version` ⇒ mismos results (salvo failed).

---

## 8. Decision History

### 8.1 Decision

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| company_id | ID | sí | |
| number | Count | sí | correlativo por empresa (#024) |
| title | Text | sí | |
| decision_pack_id | DecisionPackId | sí | |
| decision_date | Date | sí | |
| status | DecisionStatus | sí | |
| scenario_id | ID | sí | escenario congelado de la decisión |
| model_version_id | ID | sí | |
| engine_version | Text | sí | |
| calculation_run_id | ID | sí* | *obligatorio si status ∈ {approved, rejected, executed} |
| forecast_metrics | JSON | sí* | *obligatorio si status ≠ draft |
| frozen_projection | JSON | no | subset P&L/caja previsto |
| rationale | Text | sí* | *obligatorio si status ∈ {approved, rejected, executed}; vacío permitido en draft/deferred/cancelled |
| owner_user_id | ID | sí | |
| owner_label | Text | no | ej. "CEO" |
| discarded_alternatives | JSON | sí | array `{label, reason}`; puede `[]` |
| accepted_risks | JSON | sí | array `{text}`; puede `[]` |
| conditions | Text | no | |
| policy_exceptions | JSON | sí | puede `[]` |
| calibrated_scenario_id | ID | no | si se usó escenario calibrado |
| created_at | Timestamp | sí | |
| updated_at | Timestamp | sí | |

**Reglas de estado:**
- `draft` → rationale puede vacío; forecast_metrics puede vacío
- `approved|rejected|executed` → rationale + forecast_metrics + scenario_id + calculation_run_id obligatorios
- `executed` ⇒ puede recibir `ActualResult`
- Transiciones permitidas (MVP):  
  `draft → approved|rejected|deferred|cancelled`  
  `approved → executed|cancelled`  
  `deferred → draft|approved|cancelled`  
  No reabrir `executed` sin ADR.

### 8.2 DecisionMilestone

| Campo | Tipo | Req |
|---|---|---|
| id | ID | sí |
| decision_id | ID | sí |
| due_date | Date | sí |
| label | Text | sí | ej. `revisión 6 meses` |
| status | MilestoneStatus | sí |
| notes | Text | no |

### 8.3 ActualResult

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| decision_id | ID | sí | |
| period_year_month | YearMonth | sí | |
| variable_key | Text | sí | ej. `sales_monthly`, `gross_margin_pct`, `capex_total` |
| forecast_value | Decimal | sí | |
| actual_value | Decimal | sí | |
| deviation_pct | Decimal | no | calculado: `(forecast-actual)/forecast` si forecast≠0 |
| source | DataOrigin | sí | |
| recorded_by | ID | no | |
| recorded_at | Timestamp | sí | |
| notes | Text | no | |

Único `(decision_id, period_year_month, variable_key)`.

### 8.4 BiasProfile

| Campo | Tipo | Req | Notas |
|---|---|---|---|
| id | ID | sí | |
| company_id | ID | sí | |
| decision_pack_id | DecisionPackId | sí | |
| variable_key | Text | sí | |
| n_observations | Count | sí | |
| median_bias | Rate | sí | mediana de desviaciones |
| mean_bias | Rate | no | |
| std_dev | Rate | no | |
| direction | BiasDirection | sí | |
| confidence | Confidence | sí | según umbrales siguientes |
| updated_at | Timestamp | sí | |

Único `(company_id, decision_pack_id, variable_key)`.

Umbrales de comunicación (cerrados):

| n | confidence | Comunicación |
|---|---|---|
| 1–2 | low | solo casos individuales; no frase de “tendencia” |
| 3–5 | medium | “en las últimas N decisiones similares, la desviación fue…” |
| 6–9 | medium | “parece haber una tendencia a…” |
| ≥10 | high | “sistemáticamente…” |

---

## 9. Datos, importación y calidad

### 9.1 DataSource

| Campo | Tipo | Req |
|---|---|---|
| id | ID | sí |
| company_id | ID | sí |
| source_type | Enum | sí | `excel_template \| accounting_export \| manual \| api_holded \| api_odoo \| bank` |
| name | Text | sí |
| config | JSON | no |
| last_sync_at | Timestamp | no |
| status | DataSourceStatus | sí |

En MVP realistas: `excel_template`, `accounting_export`, `manual`.

### 9.2 ImportRun

| Campo | Tipo | Req |
|---|---|---|
| id | ID | sí |
| data_source_id | ID | sí |
| company_id | ID | sí |
| started_at | Timestamp | sí |
| finished_at | Timestamp | no |
| status | ImportStatus | sí |
| rows_processed | Count | no |
| quality_report | JSON | sí | huecos, outliers, unmapped |
| target_model_version_id | ID | no |

### 9.3 AccountMapping

| Campo | Tipo | Req |
|---|---|---|
| id | ID | sí |
| company_id | ID | sí |
| source_account | Text | sí |
| source_description | Text | no |
| target_category | AccountTargetCategory | sí | |
| confidence | Confidence | sí |
| confirmed | bool | sí |
| confirmed_by | ID | no |

### 9.4 ModelQualityReport (derivado, no tiene por qué ser tabla)

Calculado al vuelo o cacheado:

```text
{
  "sales_history_months": 36,
  "costs_history_months": 36,
  "collection_days": "estimated|measured",
  "inventory_modeled": false,
  "payroll_detail": "aggregated|detailed",
  "overall": "high|medium|low",
  "limitations": ["..."]
}
```

---

## 10. Trust / auditoría

### 10.1 AuditLog

| Campo | Tipo | Req |
|---|---|---|
| id | ID | sí |
| company_id | ID | sí |
| user_id | ID | no |
| entity_type | Text | sí |
| entity_id | ID | sí |
| action | Enum | sí | `create \| update \| delete \| lock \| calculate \| export \| status_change` |
| old_value | JSON | no |
| new_value | JSON | no |
| timestamp | Timestamp | sí |
| ip | Text | no | opcional |

Append-only.

---

## 11. Mapeo Snapshot → CalculationInput

Función normativa: `to_calculation_input(snapshot, scenario) -> CalculationInput`

### 11.1 `months_between`

```text
months_between(anchor: YYYY-MM, target: YYYY-MM) -> int
  = (year(target) - year(anchor)) * 12 + (month(target) - month(anchor))
```

Ejemplos:  
`months_between(2027-01, 2027-01) = 0`  
`months_between(2027-01, 2027-09) = 8`  
`months_between(2027-01, 2026-10) = -3`

### 11.2 Pasos

1. Validar `schema_version == "1.0"`
2. `H = scenario.horizon_months` (`H >= 1`)
3. `anchor = scenario.anchor_year_month`
4. Aplicar `scenario.overrides` → `effective_snapshot`
5. Mapear cada entidad con fechas:
   - `start_t = months_between(anchor, start_year_month)`
   - `end_t = months_between(anchor, end_year_month)` si existe
   - **Reglas MVP si `start_t < 0`:** si la entidad sigue activa en el horizonte (`end` null o `end_t >= 0`), usar `start_t = 0` (ya en régimen al ancla). Si `end_t < 0`, **excluir** la entidad.
   - Si `start_t >= H`, excluir (empieza fuera del horizonte)
6. Loans: `disbursement_t = months_between(anchor, disbursement_year_month)`; mapear grace según §6.5
7. Assets: `acquisition_t = months_between(...)`;  
   `acquisition_funding`: motor espera `cash | loan_id | mixed` en su boceto — **mapper envía** al CalculationInput del motor:  
   - funding `cash` → sin loan  
   - funding `loan` → asociar `funding_loan_id`  
   - funding `mixed` → loan_id + one-off/equity según notes del pack  
   (El adapter documenta el shape exacto alineado con `MOTOR_FINANCIERO` §4.1)
8. Investments → `capex_schedule` con `t`; expandir `own_funds_*` a one-off implícito (§6.7.1)
9. `assumptions_resolved = { a.key: a.value for a in assumptions }`
10. Rellenar `company`, `fiscal`, `policies`, flags `auto_finance_*` desde scenario
11. Validar input (reglas del motor §6.1)
12. `inputs_hash = sha256(canonical_json(calculation_input))`

### 11.3 Canonical JSON para hash

- Claves de objetos ordenadas alfabéticamente (recursivo)
- Arrays en orden de persistencia (no reordenar por id salvo que se documente)
- Decimals como string con escala fija canónica (money: 2 dec; rates: sin notación científica; trim de ceros solo según regla fija en código)
- Sin campos `null` opcionales omitidos de forma consistente (preferible: omitir claves null)

Mismo input lógico ⇒ mismo hash.

---

## 12. Serialización JSON de resultados

`CalculationRun.results` debe poder rehidratar el `CalculationResult` del motor:

- arrays indexados por `t`
- Decimals como string (`"1234.56"`) para no perder precisión
- `undefined` métricas como `null` + `warnings`

---

## 13. Invariantes de integridad (BD / dominio)

1. Una sola `ModelVersion.is_current = true` por `company_id`
2. Todo registro de negocio aislado por `company_id` en queries
3. `Decision.number` único por company y monotónico al asignar
4. No borrar físicamente `CalculationRun` referenciado por `Decision`
5. `Scenario.locked` no admite update de overrides
6. Overrides solo con `entity_type`/`field` del schema snapshot
7. `ActualResult.deviation_pct = (forecast - actual) / forecast` si forecast ≠ 0; si forecast = 0 y actual ≠ 0 → `null` + warning
8. Currency del snapshot = `EUR` en MVP
9. `Asset.investment_id` ↔ `Investment.linked_asset_ids` coherentes
10. `auto_finance_deficits=true` ⇒ `auto_finance_config` presente y válido
11. No duplicar own_funds (Investment) + OneOff equity del mismo hecho

---

## 14. Catálogo canónico de `variable_key` (ActualResult / Bias)

Inicial (extensible solo con ADR + update de este doc):

```text
sales_monthly
gross_margin_pct
capex_total
rent_monthly
headcount
payroll_monthly
min_cash
payback_months
revenue_ramp_month_to_breakeven
```

No crear keys ad hoc en código sin añadirlas aquí.

---

## 15. Privacidad y retención (mínimo)

- Datos financieros solo del `company_id` autorizado
- Exportaciones registradas en `AuditLog`
- En desarrollo local: BD local, sin cloud de pago obligatorio
- Los datos **no** se usan para entrenar modelos compartidos (declaración de producto)

---

## 16. Fuera de alcance v0.1

- Multi-divisa / multi-país fiscal
- Tablas normalizadas paralelas al snapshot (ver §5.1.1)
- Soft-delete complejo de todo el grafo
- Event sourcing completo
- Warehouses analíticos
- Conectores API reales Holded/Odoo (valores de `source_type` reservados)

---

## 17. Criterios de aceptación de esta spec

1. Schema JSON/Pydantic de `CompanyTwinSnapshot` alineado con §5.2–§6  
2. `to_calculation_input` implementable solo con esta spec + `MOTOR_FINANCIERO`  
3. Caso “nueva tienda + préstamo” expresable en snapshot + scenario + overrides  
4. Decision + ActualResult + BiasProfile cubren Twin Loop  
5. Sin float en campos money/rate del schema  
6. Inventario marca este archivo como **Hecho**

---

## 18. Changelog

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-03 | Primera spec de modelo de datos MVP |
| 1.1 | 2026-10-03 | Auditoría: opening_cash solo en snapshot; persistencia JSON única; auto_finance_config; overrides canónicos; months_between + hash; grace none→motor; own_funds sin doble; rationale condicional; enums cerrados; invariantes bidireccionales |
| 1.1.1 | 2026-10-03 | Overrides alineados con BuildOp de DECISION_PACKS (`add_entity` \| `set_field`) |

---

*Normativa de datos: API, ORM y motor adapter deben conformarse a este documento.*

### Nota de honestidad (post-auditoría)

La v1.0 **no estaba perfecta**: había ambigüedad de persistencia, campos obligatorios contradictorios, huecos respecto al motor (`auto_finance_config`, mapper de fechas) y tipos flojos.  
La v1.1 cierra eso lo bastante para implementar sin inventar. Seguirán saliendo bordes al codear: se resuelven con ADR + bump de esta spec, no con supuestos silenciosos.