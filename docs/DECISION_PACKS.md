# DECISION PACKS — Especificación MVP

**Finance Twin Decision Packs**  
Versión de spec: `1.1` *(revisión post-auditoría)*  
Estado: lista para implementación  
Referencias: [`PRODUCTO.md`](PRODUCTO.md) §7, §13 · [`MODELO_DATOS.md`](MODELO_DATOS.md) · [`MOTOR_FINANCIERO.md`](MOTOR_FINANCIERO.md)

---

## 0. Propósito

Un **Decision Pack** es una plantilla cerrada de decisión: inputs, construcción del escenario, métricas, análisis e informe.

- El usuario no “monta un modelo”: elige una decisión de negocio.
- El pack **no calcula**: construye un `Scenario` (+ entidades vía overrides / entidades nuevas en snapshot efectivo) y llama al motor.
- Si un pack no está en este documento, **no se implementa** en MVP.
- IDs canónicos = enum `DecisionPackId` de `MODELO_DATOS.md`.

Constraint: presupuesto 0 € — packs = lógica pura en código, sin servicios de pago.

---

## 1. Packs del MVP (cerrado)

| ID | Nombre UI | Pregunta que responde |
|---|---|---|
| `new_site` | Nuevo establecimiento | ¿Qué pasa si abro / amplío un local o sede? |
| `financing` | Financiación | ¿Qué pasa si pido (o cambio) un préstamo? |
| `asset_purchase` | Compra de activo | ¿Qué pasa si compro maquinaria, vehículo o similar? |
| `hiring` | Contratación | ¿Qué pasa si incorporo personal? |
| `generic_investment` | Inversión genérica | ¿Compensa una inversión con CAPEX y retorno? |
| `liquidity_plan` | Plan de liquidez | ¿Cómo queda la caja a 6–12 meses bajo hipótesis? |

Fuera de MVP (reservado, no implementar ahora): precios, comprar vs leasing como pack dedicado, refinanciación compleja, M&A, dividendos.

> Nota: comparar contado vs préstamo vs leasing se puede hacer en `asset_purchase` con **alternativas** (§3.5), sin pack extra.

---

## 2. Anatomía común de un pack

Todo pack implementa el mismo contrato:

```text
DecisionPackSpec
├── id: DecisionPackId
├── name_ui, description_ui
├── intent_examples[]          # frases para clasificar (chat / UI)
├── inputs_required[]
├── inputs_optional[]
├── default_resolvers[]        # cómo proponer valores desde el twin
├── build_plan                 # qué entidades / overrides crea
├── scenario_defaults          # H, discount_rate, variantes
├── metrics_primary[]
├── metrics_secondary[]
├── sensitivity_vars[]
├── inverse_sensitivity[]      # {metric, threshold_rule}
├── stress_tests[]
├── policies_to_check[]
├── quality_questions[]
├── similar_decision_keys[]    # para BiasProfile / historial
├── actual_variable_keys[]     # para Plan vs Real
├── milestones_default[]       # 3m, 6m, 12m…
└── report_template_id
```

### 2.1 Input field schema

```text
PackInput
├── key                 # estable, snake_case
├── label_ui
├── value_type          # money | rate | count | year_month | text | bool | enum | money_breakdown
├── required            # bool
├── help_ui?
├── enum_values?        # si enum
├── unit?
├── min?, max?
└── default_resolver?   # id de resolver (§2.2)
```

### 2.2 Default resolvers (catálogo MVP)

| Resolver ID | Comportamiento |
|---|---|
| `avg_bu_revenue` | Media de `base_monthly_revenue` de streams con `business_unit` tipo store/line activos |
| `company_gross_margin` | Media ponderada por revenue de `gross_margin_pct` (o mediana si n pequeño) |
| `avg_employer_cost` | Media de `monthly_employer_cost` del payroll actual |
| `hist_ramp_or_linear` | Si hay aperturas previas con ActualResult, usar rampa media; si no, rampa lineal 12 meses 0.25→1.0 |
| `debt_cost_plus_premium` | Media TIN préstamos activos + 0.02 (floor 0.05) → discount_rate |
| `policy_min_cash` | `policies.min_cash` |
| `none` | Sin default: obligatorio preguntar |

Todo default lleva `origin` + `confidence` al guardarse (user / historical / calculated / sector).

### 2.3 Build plan — reglas de oro

1. **Nunca muta** el `ModelVersion` base ni el escenario base de la empresa.
2. Crea un `Scenario` hijo con `scenario_type` adecuado y `overrides` + **entidades nuevas** embebidas en el snapshot efectivo.
3. Implementación MVP recomendada del “snapshot efectivo”:
   - Clonar snapshot base en memoria
   - Añadir entidades nuevas (streams, costs, loans…) con IDs nuevos
   - Opcionalmente aplicar overrides sobre entidades existentes
   - Persistir: `base_model_version_id` + `overrides` que describan altas (`op: add_entity`) **o** guardar `calculation_input` ya materializado en el `CalculationRun` (el Scenario guarda overrides estructurados §2.4)
4. Anti doble CAPEX: assets ligados a investment según `MODELO_DATOS`.
5. El pack **no** escribe `Decision` hasta el paso de registro explícito del usuario.

### 2.4 Override / build ops (extensión normativa del modelo)

`MODELO_DATOS` §7.2 define `set_field`. Los packs **extienden** `Scenario.overrides` con operaciones discriminadas:

```text
BuildOp
├── op: add_entity | set_field
├── entity_type     # igual que MODELO §7.2
├── entity_id       # obligatorio; nuevo UUID si add_entity
├── field?          # obligatorio si set_field
├── value?          # obligatorio si set_field
├── payload?        # objeto entidad completo si add_entity
└── justification?
```

Lista ordenada `build_ops[]` = contenido de `Scenario.overrides`.  
`set_field` ≡ override clásico. `add_entity` añade al snapshot efectivo antes de mapear al motor.

**Orden de aplicación:** todos los `add_entity` primero (en orden), luego `set_field` (en orden).

### 2.5 Modelado de ahorros de opex (norma única)

Los `CostItem.amount_monthly` son **Money ≥ 0**. No existen costes negativos.

Si un pack tiene `opex_savings_monthly` (o benefit tipo reducción de opex):

1. Si el usuario indica `cost_item_id_to_reduce`:  
   `set_field` → `amount_monthly = max(0, current - savings)`  
2. Si no hay coste que reducir y sí hay `revenue_uplift`: solo uplift  
3. Si solo hay ahorro: crear `RevenueStream`  
   - name: `Ahorro opex (equivalente)`  
   - `base_monthly_revenue = savings`  
   - `gross_margin_pct = 1.0` (sin COGS)  
   - `collection_days = 0`  
   - warning obligatorio: modelado equivalente a EBITDA, no asiento contable de coste negativo

### 2.6 Calibración — fórmula unificada

`BiasProfile.median_bias` usa la misma definición que `ActualResult.deviation_pct`:

```text
bias = (forecast - actual) / forecast     # si forecast ≠ 0
```

Valor calibrado:

```text
calibrated = user_value * (1 - median_bias)
```

Ejemplos:  
- Ventas sobreestimadas 18 % → bias=+0.18 → calibrated = user × 0.82  
- CAPEX infraestimado 9 % (forecast<actual) → bias=−0.09 → calibrated = user × 1.09  

No usar fórmulas distintas por variable.  
Solo ofrecer calibración si `n_observations >= 3` (mensajes según umbrales de `MODELO_DATOS`).

---

## 3. Flujo runtime (todos los packs)

```text
1. select_pack / classify_intent
2. load_current_twin_snapshot
3. resolve_defaults → formulario
4. user_confirm_inputs (cada valor: origin/confidence)
5. find_similar_decisions → mostrar BiasProfile si n>=3
6. offer calibrated scenario (sí/no)
7. build_ops → scenario_base (+ conservative + adverse)
8. calculate (motor) × N escenarios
9. sensitivity + inverse_sensitivity + stress + policy_checks
10. render report_template
11. user may adjust inputs → rebuild from 7
12. register Decision (status, rationale, …) + milestones
```

### 3.1 Variantes automáticas

Salvo que el pack diga lo contrario, siempre se generan:

| Variante | Regla MVP |
|---|---|
| `base` | Inputs del usuario |
| `conservative` | Ventas/efectos positivos × 0.85; costes variables/opex relevantes × 1.05 (según pack) |
| `adverse` | Ventas × 0.70; costes × 1.10; retraso apertura +2 meses si aplica |

Si el usuario acepta calibración: adicional `calibrated` aplicando §2.6 a las `actual_variable_keys` numéricas del pack presentes en BiasProfile.

### 3.2 Políticas a comprobar (unión por defecto)

- `min_cash`
- `max_debt_ebitda` (si hay deuda)
- `min_dscr` (si hay servicio de deuda)
- `max_payback_months` / `min_irr` (si hay métricas de inversión)

### 3.3 Informe estándar (`report_executive_v1`)

1. Decisión planteada  
2. Cumplimiento de políticas + riesgos (no “hazlo/no lo hagas”)  
3. Métricas primarias  
4. Caja mínima y necesidad de financiación  
5. Escenarios comparados  
6. Sensibilidad inversa (“qué tendría que pasar”)  
7. Hipótesis y orígenes  
8. Anexo de trazabilidad (links a CalculationRun)

Variante banco: `report_bank_v1` (misma base + DSCR y stress de servicio de deuda).

### 3.4 Hitos por defecto

| Mes | Label |
|---|---|
| +3 | Revisión 3 meses |
| +6 | Revisión 6 meses |
| +12 | Revisión 12 meses |

### 3.5 Alternativas (opcional por pack)

Un pack puede construir **N escenarios hermanos** (mismo problema, distinto funding/timing) y una tabla comparativa.  
No sustituye el registro de una decisión: el usuario elige cuál queda como `scenario_id` de la Decision.

---

## 4. Clasificación de intención (para UI/chat)

| Pack | Ejemplos de frase |
|---|---|
| `new_site` | “abrir tienda”, “segundo local”, “nueva sede”, “ampliar el almacén” *(ampliación física grande → new_site; si solo CAPEX sin ventas nuevas → asset/generic)* |
| `financing` | “pedir un préstamo”, “línea de crédito”, “financiar con el banco” |
| `asset_purchase` | “comprar furgoneta”, “máquina”, “equipos”, “contado o leasing” |
| `hiring` | “contratar”, “ampliar plantilla”, “sumar comerciales” |
| `generic_investment` | “invertir X €”, “proyecto con retorno”, “digitalización / obra con payback” |
| `liquidity_plan` | “¿aguanto el año?”, “tensión de caja”, “previsión 13 semanas/12 meses” |

Si ambigüedad: preguntar confirmación de pack antes de inputs.

---

## 5. Pack `new_site`

### 5.1 Meta

- **UI:** Nuevo establecimiento  
- **Descripción:** Simula apertura o nueva unidad de negocio con ventas, costes, CAPEX y financiación.  
- **Report:** `report_executive_v1` (+ `report_bank_v1` si hay deuda)

### 5.2 Inputs

| key | type | req | default_resolver | Notas |
|---|---|---|---|---|
| `site_name` | text | sí | none | |
| `open_year_month` | year_month | sí | none | |
| `capex_total` | money | sí | none | |
| `capex_breakdown` | money_breakdown | no | none | obra, mobiliario, equipos, stock_inicial, licencias; si falta, 100% `capex_total` en una línea |
| `sales_run_rate` | money | sí | avg_bu_revenue | €/mes régimen, base imponible |
| `sales_ramp_months` | count | no | — | default 12 |
| `sales_ramp` | rate[] | no | hist_ramp_or_linear | longitud = ramp_months |
| `collection_days` | count | no | — | default = mediana collection_days de streams existentes, o 30 |
| `gross_margin_pct` | rate | sí | company_gross_margin | |
| `rent_monthly` | money | sí | none | |
| `other_opex_monthly` | money | no | none | fijo mensual adicional |
| `other_opex_pct_sales` | rate | no | none | si ambos, se suman |
| `headcount` | count | no | none | default 0 |
| `employer_cost_per_person` | money | cond | avg_employer_cost | req si headcount>0 |
| `debt_amount` | money | no | none | default 0 |
| `equity_amount` | money | no | none | default = max(0, capex_total - debt_amount) |
| `loan_term_months` | count | cond | — | req si debt>0; default 84 |
| `loan_annual_rate` | rate | cond | — | req si debt>0 |
| `loan_grace_months` | count | no | — | default 0 |
| `loan_grace_type` | enum | cond | — | req si grace>0; `capital` \| `total` |
| `loan_system` | enum | no | — | default french |
| `pre_open_months` | count | no | — | default 0; meses de proyección antes de abrir (CAPEX puede adelantarse) |
| `horizon_months` | count | no | — | default 84 |
| `discount_rate_annual` | rate | no | debt_cost_plus_premium | |

**Validación funding:**

```text
funded = debt_amount + equity_amount
si funded < capex_total → ERROR (faltan fondos; el pack no activa auto_finance solo)
si funded > capex_total → WARNING (exceso queda como caja)
```

CAPEX en caja en `open_year_month - pre_open_months` si `pre_open_months>0` y el usuario no indica otro schedule; MVP: un solo desembolso en `max(anchor, open - pre_open)` — default desembolso en `open_year_month` salvo input futuro. **Norma v1.1:** desembolso CAPEX en `open_year_month`; `pre_open_months` solo alarga el horizonte hacia atrás cambiando `anchor = open_year_month - pre_open_months` (sin CAPEX anticipado automático).

### 5.3 Build ops (base)

1. `anchor_year_month = open_year_month - pre_open_months` (clamp: no negativo en calendario; si open es el ancla mínima del twin, anchor=open)  
2. `BusinessUnit` nuevo: name=`site_name`, `unit_type=store`  
3. `RevenueStream`: bu=nuevo, start=`open_year_month`, base=`sales_run_rate`, ramp, margin, `collection_days`  
4. `CostItem` rent: fixed `rent_monthly`, start=`open_year_month`  
5. `CostItem` other opex fixed y/o `variable_pct_revenue`  
6. `PayrollLine` si headcount>0, start=`open_year_month`  
7. `Investment` con `capex_schedule=[{open_year_month, capex_total}]`, links a entidades nuevas; `own_funds_*` si equity>0  
8. `Asset`(s) según breakdown o uno agregado, `investment_id` ligado (anti doble CAPEX)  
9. `Loan` si debt>0: principal=debt, disbursement=`open_year_month`, grace según inputs  
10. Scenario `base` + variantes §5.8; no mutar ModelVersion current

### 5.4 Métricas

**Primarias:** VAN, TIR, payback_simple, payback_discounted, min_cash, financing_need.max_shortfall  

**Secundarias:** debt/EBITDA pico, DSCR mínimo, mes de caja mínima

### 5.5 Sensibilidad / inversa / stress

**Sensibilidad:** `sales_run_rate`, `gross_margin_pct`, `capex_total`, `rent_monthly`, `loan_annual_rate`  

**Inversa (umbrales):**  
- VAN = 0 respecto a sales, margin, capex  
- min_cash = policy.min_cash respecto a sales  

**Stress:** ventas −15/−30 %; apertura +2/+4 meses; tipo +200 pb si hay deuda

### 5.6 Quality questions

- ¿La rampa contempla meses de obra / licencia?  
- ¿El CAPEX incluye IVA / stock inicial?  
- ¿Hay canibalización de otras unidades? (MVP: solo pregunta; no modela canibalización salvo override manual)

### 5.7 Actual / bias keys

`sales_monthly`, `gross_margin_pct`, `capex_total`, `rent_monthly`, `headcount`, `payroll_monthly`, `min_cash`, `payback_months`, `revenue_ramp_month_to_breakeven`

### 5.8 Conservative / adverse específicos

- conservative: sales×0.85, opex×1.05, ramp más lenta (×0.9 en primeros 6 meses)  
- adverse: sales×0.70, capex×1.10, open +2 months, opex×1.10

---

## 6. Pack `financing`

### 6.1 Meta

Simula disponer un préstamo (y opcionalmente el uso de fondos: CAPEX, colchón de caja, o genérico).

### 6.2 Inputs

| key | type | req | default |
|---|---|---|---|
| `loan_name` | text | sí | “Préstamo {fecha}” |
| `principal` | money | sí | — |
| `disbursement_year_month` | year_month | sí | — |
| `annual_rate` | rate | sí | — |
| `term_months` | count | sí | — |
| `system` | enum | no | french |
| `grace_months` | count | no | 0 |
| `grace_type` | enum | cond | req si grace>0 (`capital` \| `total`) |
| `origination_fee` | money | no | 0 |
| `use_of_funds` | enum | sí | `cash_buffer` \| `capex` \| `refinance_placeholder` \| `general` |
| `linked_capex` | money | cond | req si use=capex; >0 |
| `horizon_months` | count | no | 36 |
| `discount_rate_annual` | rate | no | = annual_rate |

**Validación:** si `grace_months>0` y falta `grace_type` → ERROR.  
`refinance_placeholder`: WARNING fijo — no cancela préstamos existentes en MVP.

### 6.3 Build

1. Add `Loan` (disbursement, schedule fields)  
2. `cash_buffer` / `general`: solo drawdown (caja ↑)  
3. `capex`: `Investment` + `capex_schedule` mismo mes + `linked_loan_ids`; Asset opcional; **no** duplicar OneOff capex  
4. Variantes: rate +100/+300 pb (adverse/conservative tipificadas); no bajar principal salvo stress explícito

### 6.4 Métricas primarias

min_cash, max_shortfall, DSCR_min, debt_ebitda_peak, total_interest, first_amortizing_payment

### 6.5 Sensibilidad / inversa

- Sens: `annual_rate`, `term_months`, `principal`  
- Inversa: `min_cash` vs policy respecto a rate; `DSCR` vs `policy.min_dscr` respecto a rate

### 6.6 Actual keys

`min_cash`  
+ `capex_total` si `use_of_funds=capex`

### 6.7 Quality questions

- ¿La cuota cabe en el mes de caja más flojo?  
- ¿Hay comisiones / seguros no modelados?

---

## 7. Pack `asset_purchase`

### 7.1 Meta

Compra de activo con alternativas de pago.

### 7.2 Inputs

| key | type | req | default |
|---|---|---|---|
| `asset_name` | text | sí | — |
| `acquisition_cost` | money | sí | — |
| `acquisition_year_month` | year_month | sí | — |
| `useful_life_months` | count | sí | — |
| `residual_value` | money | no | 0 |
| `depreciation_method` | enum | no | straight_line |
| `funding_mode` | enum | sí | `cash` \| `loan` \| `leasing_as_cost` |
| `loan_principal` | money | cond | default = acquisition_cost si loan |
| `loan_annual_rate` | rate | cond | |
| `loan_term_months` | count | cond | |
| `loan_grace_months` | count | no | 0 |
| `loan_grace_type` | enum | cond | |
| `leasing_monthly` | money | cond | si leasing_as_cost |
| `leasing_term_months` | count | cond | |
| `opex_savings_monthly` | money | no | 0 |
| `cost_item_id_to_reduce` | id | no | para aplicar §2.5 |
| `revenue_uplift_monthly` | money | no | 0 |
| `horizon_months` | count | no | max(useful_life, leasing_term, 60) |
| `discount_rate_annual` | rate | no | debt_cost_plus_premium |
| `compare_funding_modes` | bool | no | default false; si true → §7.4 |

### 7.3 Build

**Modo `cash` / `loan`:**
1. `Investment` + `capex_schedule`  
2. `Asset` ligado (`investment_id`)  
3. Si `loan`: `Loan` + links; funding coherente con MODELO/motor  
4. Uplift/ahorro según §2.5

**Modo `leasing_as_cost`:**
1. **No** CAPEX de compra ni Asset depreciable de adquisición  
2. `CostItem` fixed `leasing_monthly` durante `leasing_term_months`  
3. Warning: simplificación (no norma contable de leasing)  
4. Uplift/ahorro según §2.5  
5. Métricas VAN/TIR de “compra” **no aplican** a esta alternativa; informar impacto en caja y coste total del leasing. En comparativa §7.4 usar criterios de caja/desembolso, no forzar VAN de asset.

### 7.4 Alternativas automáticas

Si `compare_funding_modes=true`, generar escenarios hermanos `cash`, `loan`, `leasing_as_cost` (omitir los que falten inputs) con la **misma** utilidad operativa (savings/uplift). Tabla comparativa: desembolso inicial, caja mínima, coste nominal total, políticas.

### 7.5 Métricas

- cash/loan: VAN/TIR/payback (FCF before financing), min_cash, shortfall  
- leasing: min_cash, shortfall, total_leasing_payments; VAN opcional solo sobre flujos diferenciales vs “no hacer nada”

### 7.6 Actual keys

`capex_total` (si cash/loan), `min_cash`, `sales_monthly` (si uplift), `payback_months` (si aplica)

---

## 8. Pack `hiring`

### 8.1 Inputs

| key | type | req | default |
|---|---|---|---|
| `role_name` | text | sí | — |
| `headcount` | count | sí | — |
| `employer_cost_per_person` | money | sí | avg_employer_cost |
| `start_year_month` | year_month | sí | — |
| `end_year_month` | year_month | no | — |
| `expected_monthly_revenue_uplift` | money | no | 0 |
| `uplift_ramp` | rate[] | no | hist_ramp_or_linear / 6 meses |
| `gross_margin_pct` | rate | cond | company_gross_margin si uplift>0 |
| `horizon_months` | count | no | 24 |
| `discount_rate_annual` | rate | no | debt_cost_plus_premium |

### 8.2 Build

- PayrollLine(s)  
- Si uplift>0: RevenueStream ligado (bu opcional)  
- Conservative: uplift×0.7; adverse: uplift=0 y cost×1.0 (solo coste)

### 8.3 Métricas

min_cash, shortfall, ΔEBITDA, meses hasta uplift > cost (si uplift>0), payback simple del coste acumulado vs margen del uplift

### 8.4 Actual keys

`headcount`, `payroll_monthly`, `sales_monthly`, `min_cash`

### 8.5 Quality questions

- ¿El coste incluye SS y variables?  
- ¿El uplift es atribuible o ilusión?

---

## 9. Pack `generic_investment`

### 9.1 Inputs

| key | type | req | default |
|---|---|---|---|
| `name` | text | sí | — |
| `capex_schedule` | list[{year_month,amount}] | sí | — |
| `horizon_months` | count | sí | — |
| `benefit_cadence` | enum | sí | `monthly` \| `annual` |
| `benefit_amount` | money | sí | interpretado según cadence |
| `benefit_type` | enum | sí | `opex_reduction` \| `revenue` |
| `gross_margin_pct` | rate | cond | req si benefit_type=revenue |
| `cost_item_id_to_reduce` | id | no | para opex_reduction (§2.5) |
| `debt_amount` | money | no | 0 |
| `loan_annual_rate` / term / grace… | … | cond | si debt>0 |
| `equity_amount` | money | no | |
| `discount_rate_annual` | rate | sí | debt_cost_plus_premium |

**Validación:** exactamente un `benefit_amount` + cadence; si `opex_reduction` sin `cost_item_id_to_reduce`, aplicar §2.5.3 (stream equivalente).

### 9.2 Build

- `Investment` + `capex_schedule`  
- `revenue` → RevenueStream monthly (= benefit/12 si annual)  
- `opex_reduction` → §2.5  
- Loan/equity opcional (mismas reglas funding que new_site a escala)

### 9.3 Métricas

VAN, TIR, paybacks, min_cash, shortfall

### 9.4 Sensibilidad / inversa

benefit, capex, discount_rate → VAN=0

### 9.5 Actual keys

`capex_total`, `sales_monthly` o proxy benefit, `payback_months`, `min_cash`

---

## 10. Pack `liquidity_plan`

### 10.1 Meta

No es un CAPEX: proyecta caja y tensiones. Puede incluir shocks.

### 10.2 Inputs

| key | type | req | default |
|---|---|---|---|
| `horizon_months` | count | sí | 12 |
| `sales_adjustment_pct` | rate | no | 0 | −0.10 = −10 % sobre `base_monthly_revenue` de todos los streams |
| `collection_days_delta` | count | no | 0 | se suma a cada stream (resultado ≥ 0) |
| `payment_days_delta` | count | no | 0 | se suma a costs (resultado ≥ 0) |
| `extra_monthly_opex` | money | no | 0 | |
| `one_off_outflows` | list[{year_month,amount,label}] | no | [] |
| `one_off_inflows` | list[{year_month,amount,label}] | no | [] |
| `anchor_year_month` | year_month | no | mes current del sistema (inyectado por API) |

`include_existing_debt_service` eliminado: el servicio de deuda del twin **siempre** se incluye (está en el snapshot). No hay flag para apagarlo en MVP.

### 10.3 Build

1. Para cada RevenueStream: `set_field base_monthly_revenue *= (1 + sales_adjustment_pct)`  
2. `collection_days = max(0, collection_days + delta)`  
3. Análogo payment_days en CostItems  
4. Si extra_opex>0: `add_entity` CostItem fixed  
5. OneOffs: `other_out` / `other_in`  
6. **No** calcular VAN/TIR como métricas primarias

### 10.4 Métricas primarias

min_cash, min_cash_month, months_below_policy, max_shortfall, closing_cash_series

### 10.5 Variantes

- conservative: `sales_adjustment_pct_eff = sales_adjustment_pct - 0.05`  
- adverse: `sales_adjustment_pct_eff = sales_adjustment_pct - 0.15`, `collection_days_delta += 15`  

(Los deltas son sobre el input del usuario, en Rate / días, no “pp” ambiguos en UI interna.)

### 10.6 Actual keys

`min_cash`, `sales_monthly`

### 10.7 Quality questions

- ¿Hay impuestos / pagas extras no en el twin?  
- ¿Está actualizado el opening_cash?

---

## 11. Calibración por historial (todos los packs)

Antes de calcular (paso 5–6 del flujo):

1. Buscar Decisions con mismo `decision_pack_id` y status `executed` con ActualResult  
2. Similitud MVP: mismo pack; si hay magnitud CAPEX, ratio entre 0.5 y 2.0 respecto al input actual  
3. Agregar/actualizar BiasProfile según `MODELO_DATOS`  
4. Si alguna key del pack tiene `n >= 3` → ofrecer escenario `calibrated`  
5. Aplicar §2.6 solo a keys con perfil suficiente  
6. Registrar factores en warnings del Scenario / CalculationRun

---

## 12. Mapeo pack → entidades (resumen)

| Pack | BU | Revenue | Cost | Payroll | Loan | Asset | Investment | OneOff |
|---|---|---|---|---|---|---|---|---|
| new_site | ✓ | ✓ | ✓ | ◐ | ◐ | ◐ | ✓ | ◐ equity implícito |
| financing | | | | | ✓ | | ◐ | |
| asset_purchase | | ◐ | ◐ | | ◐ | ◐* | ◐* | |
| hiring | | ◐ | | ✓ | | | | |
| generic_investment | | ◐ | ◐ | | ◐ | ◐ | ✓ | ◐ |
| liquidity_plan | | set_field | ◐ | | | | | ✓ |

\* En `leasing_as_cost` no hay Asset/Investment de compra.

---

## 13. Contrato de implementación (código)

```text
class DecisionPack(Protocol):
    id: DecisionPackId
    def inputs_schema(self) -> list[PackInput]: ...
    def resolve_defaults(self, snapshot, user_partial) -> dict: ...
    def validate_inputs(self, inputs) -> list[Issue]: ...  # error|warning
    def build(self, snapshot, inputs) -> BuiltScenarioBundle: ...
    def analysis_plan(self) -> AnalysisPlan: ...
    def actual_keys(self) -> list[str]: ...
```

`BuiltScenarioBundle`:
- `variants: { base, conservative, adverse, calibrated? }`
- cada variant: `build_ops`, `anchor_year_month`, `horizon_months`, `discount_rate_annual`, `auto_finance_deficits=false` (packs no encienden auto_finance)

Prohibido: llamar LLM dentro del pack; mutar ModelVersion persistido; inventar packs.

---

## 14. Criterios de aceptación

1. Los 6 packs tienen inputs + build + métricas + actual keys cerrados  
2. `new_site` end-to-end → build_ops → CalculationInput válido (motor + modelo)  
3. Ningún pack muta ModelVersion base  
4. Calibración solo con n≥3 y fórmula §2.6  
5. Sin CostItem negativos; ahorros vía §2.5  
6. Leasing = coste + warning; VAN de compra no forzado en leasing  
7. Funding insuficiente en new_site = ERROR (no auto_finance silencioso)

---

## 15. Changelog

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-03 | Spec MVP de los 6 Decision Packs |
| 1.1 | 2026-10-03 | Auditoría: §2.5 ahorros; §2.6 bias unificado; funding ERROR; pre_open/collection_days; financing keys limpios; leasing métricas; benefit cadence; liquidity rates; BuildOp order |

---

*Normativa: Decision Studio / API / IA solo orquestan estos packs; no inventan tipos de decisión nuevos sin actualizar este documento.*

### Nota de honestidad (post-auditoría)

La v1.0 tenía contradicciones (ahorros vs Money≥0, bias distinto por variable, keys de financing incoherentes, auto_finance ambiguo, leasing/VAN).  
La v1.1 las cierra para implementar sin inventar.