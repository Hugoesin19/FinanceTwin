# MOTOR FINANCIERO — Especificación

**Finance Twin Engine**  
Versión de spec: `1.1` *(revisión post-auditoría)*  
Versión de motor a implementar: `0.1.0`  
Estado: lista para implementación (con simplificaciones explícitas)  
Referencia de producto: [`PRODUCTO.md`](PRODUCTO.md) §11, §12, §18  
Constraint de desarrollo: **presupuesto 0 €** (stack libre; servicios de pago solo si el producto se usa de verdad)

---

## 0. Propósito de este documento

Este documento es la **especificación normativa** del motor de cálculo.

- Si una fórmula no está aquí, **no se implementa**.
- Si hay ambigüedad, se resuelve aquí primero (ADR + actualización de esta spec).
- Ni la IA ni la interfaz pueden recalcular: solo consumen resultados del motor.
- Toda implementación debe poder contrastarse con los **casos golden** de la sección 14.

Relación con otros docs:

| Documento | Relación |
|---|---|
| `PRODUCTO.md` | Visión y alcance |
| `MODELO_DATOS.md` | Formato exacto de entidades y mapper a CalculationInput |
| `VALIDACION.md` | Protocolo de prueba empírico y técnico (L0–L5, V1–V7) |
| `DECISION_PACKS.md` | Cómo se construyen escenarios; el motor solo calcula |

---

## 1. Principios no negociables

| ID | Principio | Implicación |
|---|---|---|
| M1 | **Determinista** | Mismas entradas + misma versión → mismas salidas |
| M2 | **Dinero en Decimal** | Prohibido `float`/`double` para importes y tipos especiales de dinero |
| M3 | **Mes = unidad mínima** | Todos los estados se proyectan mes a mes |
| M4 | **Un solo motor** | Un único camino de cálculo; sin “cálculos rápidos” paralelos |
| M5 | **Trazable** | Cada cifra relevante puede desglosarse a fórmula + inputs |
| M6 | **Reproducible** | Se guarda `engine_version`, `model_version` y hash de inputs |
| M7 | **Simplificaciones explícitas** | Lo aproximado se documenta; no se oculta |
| M8 | **Analytics no recalcula** | Escenarios/sensibilidad solo cambian inputs y vuelven a llamar al motor |

---

## 2. Alcance del motor v0.1 (MVP)

### 2.1 Incluido

- Horizonte de proyección mensual configurable (`H` meses, típico 12–84)
- P&L mensual
- Cash flow mensual (método directo)
- Balance simplificado mensual
- Cuadros de amortización de préstamos (francés, lineal, bullet; carencia de capital y total)
- Amortización contable de activos (lineal; acelerada opcional simple)
- IVA simplificado + Impuesto de Sociedades simplificado
- Métricas de inversión: VAN, TIR, payback simple, payback descontado
- Ratios principales
- Necesidad de financiación / caja mínima
- Comprobación de políticas (guardrails)
- Traza de cálculo (nivel suficiente para auditoría de cifras clave)

### 2.2 Excluido en v0.1 (y por qué)

| Excluido | Motivo principal | ¿Se puede hacer después? |
|---|---|---|
| **Monte Carlo** | No hace falta para el valor nuclear; sensibilidad inversa aporta más a una pyme. Añade UX/cálculo y riesgo de malinterpretar probabilidades | Sí (fase posterior) |
| **Multi-divisa** | Madagascar/pyme ES opera en EUR; FX complica caja, deuda y tests | Sí, si hay cliente que lo necesite |
| **Consolidación multi-empresa** | Fuera del ICP inicial; mucho modelo y UI | Sí (Advisor / grupos) |
| **Inventario detallado** | Útil en retail/industria, pero no bloquea abrir tienda/préstamo/CAPEX si se modela margen y compras simplificadas | Sí, tras Twin Loop básico |
| **Fiscalidad avanzada** | Créditos fiscales, bases negativas, grupos: alto esfuerzo y fácil equivocarse; un IS/IVA simple ya da caja creíble | Sí, con asesor fiscal |
| **Leasing/renting contable completo** | Norma contable densa; en MVP se modela como **coste periódico** (y si hace falta, como deuda simplificada en un loan) | Sí |
| **Inflación multi-partida** | Un `growth_annual` por entidad basta al inicio | Sí |
| **Tipos variables + curva forward** | Los préstamos pyme del piloto se pueden meter con tipo fijo/constante del momento | Sí |
| **Saldos iniciales AR/AP run-off completo** | Sin datos de antigüedad de facturas el arranque miente; mejor 0 + warning que fingir precisión | v0.2 |

**Ninguna exclusión es “porque la IA no sepa hacerlo”.**  
Son exclusiones de **producto/MVP**: o no aportan al caso de uso principal, o meten complejidad/error antes de tener el núcleo estable, o necesitan datos que la pyme aún no tiene limpios.

---

## 3. Convenciones

### 3.1 Tiempo

- El horizonte tiene `H` meses
- El tiempo se indexa por enteros `t = 0, 1, 2, …, H-1` (**exactamente H períodos**)
- `t = 0` = primer mes proyectado
- Cada período es un **mes de proyección**
- Las fechas reales (`YYYY-MM`) se mapean a `t` con `month_index(date)`
- Flujos y resultados del mes `t` se consideran **fin de mes** salvo que se indique lo contrario

### 3.2 Signos

| Concepto | Signo |
|---|---|
| Ingresos, cobros, disposición de préstamo | positivo |
| Costes, pagos, CAPEX, amortización de capital, intereses pagados | positivo en su línea de gasto/pago (se restan en fórmulas) |
| Flujo neto | positivo = entra caja; negativo = sale caja |
| Deuda viva | positivo = obligación pendiente |

### 3.3 Redondeo

| Caso | Regla |
|---|---|
| Importes monetarios mostrados | 2 decimales |
| Cálculos intermedios | precisión Decimal alta (mín. 28 dígitos de contexto) |
| Redondeo final de importes | `ROUND_HALF_UP` a 2 decimales |
| Tipos (% interés, márgenes) | almacenar en Decimal; no truncar antes de tiempo |
| Cuota de préstamo | calcular con alta precisión; redondear cuota a 2 decimales; **ajustar la última cuota** para liquidar el residual |

Regla de consistencia: tras redondear estados mensuales, los invariantes (§13) deben cumplirse con tolerancia `≤ 0.01 €` por mes (error de redondeo), salvo que el test declare tolerancia distinta.

### 3.4 Unidades

- Moneda del modelo: una sola (`EUR` en MVP)
- Porcentajes: fracción Decimal (`0.08` = 8 %) en fórmulas; la UI puede mostrar %
- Días de cobro/pago: enteros ≥ 0
- Conversión días → meses de desfase: `lag_months = floor(días / 30)`  
  **Simplificación explícita MVP.** Documentar; no pretender calendario exacto.

---

## 4. Entradas mínimas del motor

El motor recibe un **CalculationInput** inmutable.

```text
CalculationInput
├── company
│   ├── currency
│   ├── opening_cash                    # caja al inicio de t=0 (antes de flujos del mes)
│   ├── default_purchase_payment_days   # default 30; para COGS si no hay override
│   ├── fiscal
│   │   ├── vat_rate                    # ej. 0.21
│   │   ├── vat_settlement              # monthly | quarterly
│   │   ├── vat_payment_lag_months      # desfase pago liquidación (ej. 1)
│   │   ├── corp_tax_rate               # ej. 0.25
│   │   └── corp_tax_payment_mode       # none | annual_end | quarterly_approx
│   └── policies                        # CompanyPolicy (guardrails)
├── horizon_months                      # H
├── discount_rate_annual                # r anual para VAN/payback descontado (inversión)
├── auto_finance_deficits               # bool (default false)
├── auto_finance_config                 # si auto_finance=true: tipo, plazo, etc.
├── revenue_streams[]
├── cost_items[]
├── payroll[]
├── loans[]
├── assets[]
├── investments[]                       # proyectos / CAPEX programado + flujos asociados
├── one_off_cash_events[]               # eventos puntuales (aportación, dividendo, CAPEX suelto)
└── assumptions_resolved                # mapa nombre→valor ya resuelto (opcional trazabilidad)
```

### 4.1 Campos mínimos por entidad (hasta que exista MODELO_DATOS.md)

**RevenueStream**
```text
id, name, business_unit_id?
start_t, end_t?                         # inclusive start; end opcional
base_monthly_revenue                    # ingreso neto de IVA (base imponible) en régimen
ramp[]?                                 # factores 0..1 por mes desde start (si no, 1)
seasonality[12]?                        # multiplicadores mes-del-año (default 1)
growth_annual                           # aplicado anualmente compuesto sobre base, o 0
gross_margin_pct                        # 0..1 → COGS = revenue * (1 - margin)
collection_days
```

**CostItem**
```text
id, name, business_unit_id?
start_t, end_t?
nature                                  # fixed | variable_pct_revenue | per_unit (MVP: fixed | variable_pct_revenue)
amount_monthly?                         # si fixed
pct_of_revenue?                         # si variable
payment_days
growth_annual
seasonality[12]?
```

**Payroll**
```text
id, role_name, headcount
monthly_employer_cost                   # coste empresa total
start_t, end_t?
business_unit_id?
payment_days                            # default 0 (mismo mes)
```

**Loan**
```text
id, name
principal
annual_interest_rate                    # efectivo nominal anual
rate_type                               # fixed (MVP)
term_months                             # n de amortización tras carencia
amortization_system                     # french | linear | bullet
grace_months                            # 0..
grace_type                              # capital | total
disbursement_t                          # mes en que entra el principal a caja
origination_fee                         # importe (sale de caja en disbursement_t)
```

**Asset**
```text
id, name
acquisition_cost
acquisition_t
useful_life_months
residual_value                          # default 0
depreciation_method                     # straight_line | declining_simple
acquisition_funding                     # cash | loan_id | mixed
```

**Investment (proyecto)**
```text
id, name
capex_schedule[]                        # lista {t, amount}  (importe base, sin IVA o con flag)
linked_revenue_stream_ids[]
linked_cost_item_ids[]
linked_payroll_ids[]
linked_loan_ids[]
own_funds_t?                            # mes de aportación de recursos propios (si aplica)
analysis_start_t                        # inicio para métricas (normalmente primer CAPEX)
analysis_horizon_months                 # si distinto del H global
```

**OneOffCashEvent**
```text
id, t, amount, kind                     # equity_injection | dividend | other_in | other_out | capex
```

---

## 5. Salidas del motor

```text
CalculationResult
├── engine_version
├── model_version?                      # si el caller lo aporta
├── inputs_hash
├── horizon_months
├── pnl[t]                              # MonthlyPnL
├── cash_flow[t]                        # MonthlyCashFlow
├── balance[t]                          # MonthlyBalance (fin de mes)
├── loan_schedules[loan_id]             # filas mensuales
├── asset_schedules[asset_id]
├── investment_metrics[investment_id]?  # si hay investments; también métricas globales opcionales
├── ratios[t]
├── financing_need                      # resumen
├── policy_checks[]
├── warnings[]                          # simplificaciones, datos faltantes, no convergencia
└── trace                               # CalculationTrace
```

### 5.1 MonthlyPnL

```text
revenue
cogs
gross_profit
payroll_expense
other_opex
ebitda
depreciation
ebit
interest_expense
ebt                                     # BAI
corp_tax_expense                        # gasto devengado (no necesariamente pago)
net_income
```

### 5.2 MonthlyCashFlow

```text
collections                             # cobros clientes (incl. IVA cobrado)
supplier_payments                       # pagos compras/costes (incl. IVA soportado pagado)
payroll_payments
other_opex_payments
vat_paid                                # liquidación IVA pagada este mes
corp_tax_paid
operating_cash_flow

capex_paid
divestment_proceeds
investing_cash_flow

loan_drawdowns
loan_principal_repaid
loan_interest_paid
equity_injections
dividends_paid
financing_cash_flow

net_cash_flow
opening_cash
closing_cash
```

### 5.3 MonthlyBalance (simplificado)

```text
# Activo
non_current_assets_net
accounts_receivable                     # saldo clientes (base+IVA pendiente de cobro) simplificado
cash
total_assets

# Pasivo + PN
debt_long_term
debt_short_term                         # principal a amortizar en ≤12 meses
accounts_payable
vat_payable                             # saldo con Hacienda (puede ser negativo = a compensar)
corp_tax_payable
equity                                  # residual para cuadrar + movimientos de capital/resultado
total_liabilities_equity
```

**Regla de cierre del balance (MVP):**  
`equity_t = total_assets_t − (deuda_total_t + accounts_payable_t + vat_payable_t + corp_tax_payable_t)`  
Es decir: el patrimonio es la **partida residual** que hace cuadrar.  
Se parte de un `equity_0` implícito al inicio y se valida que la variación de equity sea coherente con resultado + aportaciones − dividendos, con tolerancia de redondeo. Si la coherencia falla → `warning` + test rojo.

---

## 6. Pipeline de cálculo (orden obligatorio)

```text
0.  Validar inputs
1.  Construir calendario t=0..H-1
2.  Resolver series de ingresos (por stream)
3.  Resolver COGS y costes variables
4.  Resolver costes fijos + payroll
5.  Resolver amortizaciones de activos (devengo)
6.  Resolver cuadros de préstamos (devengo + caja de servicio de deuda)
7.  Componer P&L hasta EBIT / intereses / BAI
8.  Impuesto de sociedades (devengo)
9.  P&L → Resultado neto
10. Convertir devengos → caja (lags de cobro/pago + IVA)
11. Aplicar CAPEX, drawdowns, one-offs
12. Caja acumulada
13. Si auto_finance_deficits: iterar (máx N) insertando préstamo puente → volver a 6
14. Construir balance mensual
15. Ratios
16. Métricas de inversión
17. Financing need summary
18. Policy checks
19. Empaquetar traza + hash
```

### 6.1 Validación de inputs (paso 0)

Fallar duro (error) si:
- `H < 1`
- `opening_cash` ausente
- préstamo con `term_months < 1` (si grace_type requiere amortización)
- `useful_life_months < 1` en asset
- tasas fuera de rango absurdo (`< 0` o `> 1` para vat/corp tax sin justificación)
- IDs duplicados

Avisar (warning) si:
- no hay revenue streams
- `collection_days` o `payment_days` muy altos (> 180)
- `auto_finance_deficits=true` sin config
- simplificaciones activas (siempre listar las del MVP usadas)

---

## 7. Fórmulas por bloque

### 7.1 Ingresos

Para cada `RevenueStream` s y mes t:

```text
active(s,t) = (t >= s.start_t) and (s.end_t is null or t <= s.end_t)

years_from_start = floor((t - s.start_t) / 12)
growth_factor = (1 + s.growth_annual) ^ years_from_start

ramp_factor = s.ramp[t - s.start_t] if ramp defined and index exists else 1
season_factor = s.seasonality[calendar_month(t)] if defined else 1

revenue_s_t = s.base_monthly_revenue * growth_factor * ramp_factor * season_factor
              if active else 0

revenue_t = Σ_s revenue_s_t
```

`revenue` es **base imponible** (sin IVA).

### 7.2 COGS y margen bruto

```text
cogs_s_t = revenue_s_t * (1 - s.gross_margin_pct)
cogs_t = Σ_s cogs_s_t
gross_profit_t = revenue_t - cogs_t
```

Si un stream no tiene margen, error de validación (no asumir 0 en silencio).

### 7.3 Costes de explotación y personal

**CostItem fixed:**
```text
cost_t = amount_monthly * growth_factor * season_factor   si active
```

**CostItem variable_pct_revenue:**
```text
cost_t = pct_of_revenue * revenue_of_scope_t * season_factor
```
`revenue_of_scope_t` = revenue total, o de `business_unit_id` si está definido.

**Payroll:**
```text
payroll_t = Σ headcount_i * monthly_employer_cost_i   (si active; headcount ya viene en entidad)
```
En MVP `headcount` es escalar constante por fila (no hiring curve compleja).

```text
other_opex_t = Σ cost_items_t
payroll_expense_t = payroll_t
ebitda_t = gross_profit_t - payroll_expense_t - other_opex_t
```

### 7.4 Amortización de activos

**Lineal:**
```text
depreciable_base = acquisition_cost - residual_value
dep_monthly = depreciable_base / useful_life_months

si t < acquisition_t: dep = 0
si t >= acquisition_t + useful_life_months: dep = 0
si t == último mes de vida: ajustar para no pasar de depreciable_base acumulado
en otro caso: dep = dep_monthly
```

**Declining simple (opcional MVP):**
```text
rate = 2 / useful_life_months          # doble-linear simplificado mensual
dep_t = net_book_value_{t-1} * rate
cap at residual: net_book_value no baja de residual_value
```

```text
depreciation_t = Σ assets dep_t
ebit_t = ebitda_t - depreciation_t
```

CAPEX en caja:
```text
capex_paid_t += acquisition_cost en acquisition_t
               (+ IVA si flag; ver §9)
```

### 7.5 Préstamos — cuadros de amortización

Todo en **periodicidad mensual**.

```text
i = annual_interest_rate / 12
```

**Convención explícita:** `annual_interest_rate` se interpreta como **tipo nominal anual convertible mensualmente (TIN/12)**, que es lo habitual en cuadros bancarios españoles de cuota mensual.  
No es TAE ni tipo efectivo anual compuesto. Si el usuario aporta TAE, convertir *antes* de entrar al motor (fuera de scope v0.1: se documenta el tipo como TIN nominal).

Sea `D_t` el principal vivo al **inicio** del mes t (antes de la cuota del mes).

#### 7.5.1 Disposición

En `disbursement_t`:
```text
D_{disbursement} = principal
loan_drawdowns += principal
si origination_fee > 0: other financing outflow / opex fee según config
  MVP: fee sale de caja en el mismo mes (financing_cash_flow negativo)
```

#### 7.5.2 Carencia

Para meses `disbursement_t .. disbursement_t + grace_months - 1`:

**grace_type = capital:**
```text
interest_accrued_t = D_t * i
interest_paid_t = interest_accrued_t
principal_repaid_t = 0
D_{t+1} = D_t
```

**grace_type = total:**
```text
interest_accrued_t = D_t * i      # SÍ hay gasto financiero (devengo)
interest_paid_t = 0               # no sale caja
D_{t+1} = D_t + interest_accrued_t   # capitalización
```

En agregados P&L: `interest_expense_t` incluye `interest_accrued_t`.  
En caja: `loan_interest_paid_t` usa solo `interest_paid_t`.  
**No confundir “no se paga” con “no existe gasto”.**

#### 7.5.3 Sistema francés (tras carencia)

Sea `n = term_months` restantes al salir de carencia, `P = D_t` al primer mes de amortización.

```text
payment = P * i / (1 - (1+i)^(-n))     si i > 0
payment = P / n                         si i == 0
```

Cada mes de amortización:
```text
interest_accrued_t = D_t * i
interest_paid_t = interest_accrued_t
principal_repaid_t = payment - interest_paid_t
D_{t+1} = D_t - principal_repaid_t
```

Última cuota: ajustar `principal_repaid` y `payment` para que `D_final = 0` (cerrando residual por redondeo).

#### 7.5.4 Sistema lineal

```text
principal_repaid_t = P_initial_amort / n
interest_accrued_t = D_t * i
interest_paid_t = interest_accrued_t
payment_t = principal_repaid_t + interest_paid_t
```

#### 7.5.5 Bullet

Durante `term_months - 1` meses tras carencia:
```text
principal_repaid = 0
interest_accrued = D * i
interest_paid = interest_accrued
```
En el último mes:
```text
principal_repaid = D
interest_accrued = D * i
interest_paid = interest_accrued
```

#### 7.5.6 Agregados P&L / caja

```text
interest_expense_t = Σ loans interest_accrued_t   # (en amortización normal: accrued = paid)
loan_interest_paid_t = Σ loans interest_paid_t
loan_principal_repaid_t = Σ principal_repaid_t
```

En meses sin carencia total: `interest_accrued_t = interest_paid_t = D_t * i` (MVP: se paga en el mismo mes).

```text
ebt_t = ebit_t - interest_expense_t
```

---

## 8. De P&L a caja

### 8.1 Lag de cobros y pagos

Simplificación MVP: lag en meses enteros.

```text
lag_c = floor(collection_days / 30)
lag_p = floor(payment_days / 30)
```

**Cobros (por stream):**
```text
# Se cobra en t el ingreso devengado en t - lag_c
# Importe cobrado incluye IVA repercutido
collections_t += revenue_{t-lag_c} * (1 + vat_rate)   si t-lag_c >= 0
```

**Pagos de COGS / costes:**
- COGS de stream s: `company.default_purchase_payment_days` (default 30) salvo override
- CostItem: su `payment_days`
- Payroll: su `payment_days` (default 0); **sin IVA**

```text
supplier_payments_t += vatable_base_{t-lag_p} * (1 + vat_rate)
payroll_payments_t += payroll_{t-lag_pay}
other_opex_payments_t += non_cogs_cost_payments...
```

### 8.1.1 Saldos de clientes y proveedores (AR/AP)

Obligatorio para que el balance no sea decorativo.

Con IVA incluido en el stock:

```text
# Clientes: lo devengado (con IVA) aún no cobrado
AR_t = Σ_s Σ_{u=t-lag_c(s)+1 .. t} revenue_s_u * (1+vat_rate)
        (solo u>=0; si opening_ar=0 no hay run-off previo)

# Proveedores: bases vatable pendientes de pago (con IVA)
AP_t = Σ pendientes análogas de cogs/costes vatable
```

Si `lag = 0`, AR/AP de esa partida = 0 a fin de mes (se cobra/paga en el mismo mes).

**Arranque:** v0.1 usa `opening_ar = 0`, `opening_ap = 0` + warning.  
v0.2: run-off de saldos iniciales reales.

### 8.2 CAPEX y one-offs — regla anti doble conteo

```text
capex_paid_t = Σ investment.capex_schedule amounts at t
             + Σ assets.acquisition_cost at acquisition_t
               SOLO si el asset NO está ya incluido en un investment.capex_schedule
             + one_offs kind=capex
```

Regla: un desembolso de inversión aparece **una sola vez**.  
Si un `Asset` está ligado a un `Investment`, el CAPEX vive en el schedule del investment; el asset aporta amortización contable, no un segundo pago.

Si `acquisition_funding = loan_id`, el mismo mes puede haber `loan_drawdowns` (+caja) y `capex_paid` (−caja). Eso es correcto (financia la compra).

### 8.3 Acumulación de caja

```text
operating_cash_flow_t =
    collections_t
  - supplier_payments_t
  - payroll_payments_t
  - other_opex_payments_t
  - vat_paid_t
  - corp_tax_paid_t

investing_cash_flow_t = - capex_paid_t + divestment_proceeds_t

financing_cash_flow_t =
    loan_drawdowns_t
  - loan_principal_repaid_t
  - loan_interest_paid_t
  + equity_injections_t
  - dividends_paid_t
  - origination_fees_t

net_cash_flow_t = operating + investing + financing
opening_cash_0 = company.opening_cash
opening_cash_t = closing_cash_{t-1}
closing_cash_t = opening_cash_t + net_cash_flow_t
```

### 8.4 Financiación automática de déficits (opcional)

Si `auto_finance_deficits = false` (default): se permiten `closing_cash < 0` y se reportan.

Si `true`:
1. Detectar primer mes con `closing_cash_t < min_cash_target` (política o 0)
2. Insertar préstamo puente con principal ≈ déficit + colchón configurado
3. Recalcular desde préstamos (paso 6) 
4. Repetir hasta convergencia o `max_iterations = 5`
5. Si no converge → error/warning explícito

Esto debe quedar **marcado en warnings** porque altera el escenario.

---

## 9. Impuestos (simplificación MVP)

### 9.1 IVA

```text
vat_output_t = revenue_t * vat_rate
vat_input_t = (cogs_t + vatable_opex_t + vatable_capex_t) * vat_rate
vat_net_t = vat_output_t - vat_input_t
```

Liquidación:
- `monthly`: se liquida cada mes
- `quarterly`: se acumula 3 meses

Pago:
```text
vat_paid_{settlement_month + vat_payment_lag_months} += max(vat_net_settlement, 0)
```
Si negativo, se arrastra compensación (saldo `vat_payable` negativo) — MVP simple.

**Simplificación explícita:** un único `vat_rate` para toda la empresa.

### 9.2 Impuesto de sociedades

```text
# MVP: sin bases negativas complejas; si ebt_t < 0 → corp_tax_expense_t = 0 ese mes
# Opción A (mensual aproximada):
corp_tax_expense_t = max(ebt_t, 0) * corp_tax_rate

net_income_t = ebt_t - corp_tax_expense_t
```

Pago:
- `none`: solo devengo (útil para tests)
- `annual_end`: paga en el último mes del año de proyección el acumulado
- `quarterly_approx`: 3 pagos a cuenta + ajuste (simplificado)

Documentar en warnings el modo usado.

---

## 10. Métricas de inversión

Aplican a un `Investment` o a un conjunto de flujos incrementales.

### 10.1 Flujo incremental del proyecto

```text
FC_t = Δ operating_cash_flow_t + Δ investing_cash_flow_t + Δ financing_cash_flow_related?
```

Definición MVP recomendada (**free cash flow del proyecto antes de deuda**):

```text
FC_t =
    Δ collections/pagos operativos atribuibles
  - Δ capex del proyecto
  (excluye drawdowns y servicio de deuda)
```

Para decisión con financiación, el informe muestra **también** impacto en caja de la empresa (con deuda), pero VAN/TIR canónicos se calculan sobre FCF sin financiación (estándar de appraisal).  
Si se pide VAN “de equity”, documentarlo como métrica aparte.

### 10.2 VAN

`r_annual` = `discount_rate_annual`  
`r_month = (1 + r_annual)^(1/12) - 1`

```text
VAN = Σ_{t=0..T} FC_t / (1 + r_month)^t
```

Si el CAPEX inicial ya está dentro de `FC_0` (negativo), no restar I0 otra vez.  
Convención: **CAPEX va dentro de FC**; no hay resta doble.

### 10.3 TIR

TIR mensual `y` tal que:
```text
Σ FC_t / (1 + y)^t = 0
```
TIR anual:
```text
TIR_annual = (1 + y)^12 - 1
```

Algoritmo: Newton-Raphson con fallback a bisección.  
Si no hay cambio de signo en VAN → `TIR = undefined` + warning.

### 10.4 Payback

**Simple:** menor `T` tal que `Σ_{t=0..T} FC_t >= 0`  
**Descontado:** menor `T` tal que `Σ_{t=0..T} FC_t / (1+r_month)^t >= 0`

Si no se recupera en horizonte → `null` / `> H meses`.

### 10.5 ROI (simple)

```text
ROI = (Σ FC_t) / |Σ CAPEX_t|     # si CAPEX total > 0
```
Métrica auxiliar; no sustituye VAN/TIR.

---

## 11. Necesidad de financiación y caja mínima

```text
min_cash = min_t closing_cash_t
min_cash_t = argmin closing_cash_t

# Déficit respecto a política
policy_min = policies.caja_minima (default 0)
shortfall_t = max(policy_min - closing_cash_t, 0)
max_shortfall = max_t shortfall_t
first_shortfall_t = primer t con shortfall_t > 0
```

```text
financing_need = {
  min_cash,
  min_cash_month,
  max_shortfall_vs_policy,
  first_shortfall_month,
  months_below_policy: count
}
```

---

## 12. Ratios (mensuales)

Usar magnitudes del mes o ventanas cuando se indique.

| Ratio | Fórmula MVP |
|---|---|
| Margen bruto | `gross_profit / revenue` (si revenue>0) |
| Margen EBITDA | `ebitda / revenue` |
| Deuda / EBITDA | `debt_total / ebitda_ttm` (si ebitda_ttm≤0 → undefined) |
| DSCR | `ebitda_t / (principal_repaid_t + interest_paid_t)` (si denom=0 → undefined) |
| EBITDA / intereses | `ebitda / interest_expense` |
| Liquidez (proxy) | `cash / short_term_outflows_next_month` (opcional v0.1; si no, omitir) |

`ebitda_ttm` = suma 12 meses móviles; si hay menos de 12, anualizar con warning o usar suma disponible marcada como “parcial”.

---

## 13. Invariantes (siempre true)

Estos se ejecutan en tests automáticos:

1. `len(pnl) == len(cash_flow) == len(balance) == H`
2. `closing_cash_t == opening_cash_t + net_cash_flow_t` (±0.01)
3. `opening_cash_{t+1} == closing_cash_t`
4. `gross_profit_t == revenue_t - cogs_t`
5. `ebitda_t == gross_profit_t - payroll_expense_t - other_opex_t`
6. `ebit_t == ebitda_t - depreciation_t`
7. `ebt_t == ebit_t - interest_expense_t`
8. `net_income_t == ebt_t - corp_tax_expense_t` (±0.01)
9. Para cada préstamo: `D_final ≈ 0` al terminar plazo (si no matures después de H, D_H ≥ 0 y coherente)
10. Amortización acumulada ≤ `acquisition_cost - residual`
11. `balance.total_assets ≈ balance.total_liabilities_equity` (±0.05)
12. Determinismo: mismo input hash → mismo result hash

---

## 14. Casos golden (obligatorios)

Cada caso tiene inputs reducidos y resultados esperados. Sirven como tests del repo.

### G1 — VAN conocido

```text
FC = [-1000, 400, 400, 400]   # índices t=0..3
r_annual = 0
→ VAN = 200
→ payback simple: primer T con acumulado >= 0 → T = 3
```

### G2 — VAN con descuento (obligatorio, no smoke)

```text
FC = [-100, 60, 60]           # t=0..2
r_month = 0.01
→ VAN = -100 + 60/1.01 + 60/1.01^2
→ VAN = -100 + 59.405940... + 58.817762... = 18.2237 ≈ 18.22 (ROUND_HALF_UP a 2 dec)
```

Fijar expected en tests: `18.22`.

### G3 — Préstamo francés sin carencia

```text
principal = 120000
annual_rate = 0.12        # i_month = 0.01
term_months = 12
grace = 0
sistema = french
```

Comprobar:
- cuota constante (salvo última ajuste)
- interés mes t=0 (primer mes) = 120000 * 0.01 = 1200
- principal vivo final = 0
- suma principal amortizado = 120000

### G4 — Carencia de capital 3 meses

```text
igual que G3 + grace_months=3, grace_type=capital, term_months=12
```

Meses t=0..2: intereses pagados 1200, principal constante.  
Luego 12 cuotas francesas sobre 120k.

### G5 — Carencia total 2 meses

```text
principal=100000, i_month=0.01, grace_months=2, grace_type=total, luego francés n=12
```

Comprobar:
- t=0,1: `interest_paid=0`, `interest_expense=D*i`, `D` crece
- tras carencia: amortiza el principal capitalizado
- P&L del periodo de carencia tiene gasto financiero > 0 aunque la caja de intereses sea 0

### G6 — P&L simple un mes

```text
revenue = 10000
margin = 40% → cogs=6000
payroll=2000
other_opex=1000
dep=0
interest=0
tax_rate=0
→ ebitda=1000; net_income=1000
```

### G7 — Lag de cobro 30 días

```text
revenue_0 = 10000, vat=0, collection_days=30 → lag=1
opening_cash=0
costes=0
→ collections_0=0; collections_1=10000
→ closing_cash_0=0; closing_cash_1=10000
→ AR_0 = 10000; AR_1 = 0
```

### G8 — Caja mínima y shortfall

Construido para que `closing_cash` caiga a -50 en t=3 y política min=0 → max_shortfall=50, first_shortfall=3.

### G9 — Activo lineal

```text
cost=1200, residual=0, life=12, acquisition_t=0
→ dep_t = 100 cada mes t=0..11
→ acumulado=1200
```

### G10 — Determinismo

Ejecutar G3 dos veces; hashes idénticos.

### G11 — Anti doble CAPEX

Asset 50.000 ligado a Investment cuyo schedule ya incluye 50.000 en t=0 → `capex_paid_0 = 50000` (no 100000).

*(Al implementar, fijar expected numéricos exactos en JSON de tests; esta sección define el contrato.)*

---

## 15. Traza de cálculo

Mínimo viable de traza:

```text
CalculationTrace
├── steps[]: { name, started, finished }
├── series_origins: para revenue/cogs/cash key lines → lista de entity ids
├── loan_traces
├── formulas_used: mapa métrica → fórmula id
└── simplifications_applied: [ "vat_single_rate", "lag_floor_days_30", ... ]
```

Para una métrica clave (VAN, min_cash, installment):
```text
MetricTrace
├── value
├── formula_id
├── inputs: { nombre: valor }
└── dependents: ids
```

No se exige trazar cada celda mensual en v0.1, pero sí:
- VAN/TIR/payback
- caja mínima
- necesidad de financiación
- cada cuota de préstamo (vía schedule)

---

## 16. API interna del motor (contrato Python)

```python
def calculate(input: CalculationInput) -> CalculationResult:
    """Única entrada pública al motor."""

def calculate_investment_metrics(
    cash_flows: Sequence[Decimal],
    discount_rate_annual: Decimal,
) -> InvestmentMetrics:
    """Utilidad pura testeable sin modelo completo."""

def build_loan_schedule(loan: Loan, horizon: int) -> LoanSchedule:
    """Utilidad pura."""
```

Prohibido:
- leer base de datos
- llamar LLMs
- I/O de red
- tiempo no determinista dentro del cálculo (el `computed_at` lo pone el caller)

### 16.1 Stack con presupuesto 0 € (desarrollo)

El motor **no depende de ningún servicio de pago**.

| Pieza | Opción gratis |
|---|---|
| Lenguaje | Python 3 |
| Dinero / precisión | `decimal` (stdlib) |
| Tests | `pytest` |
| Repo / CI local | git + pytest en local |
| BD (más adelante) | PostgreSQL local / SQLite en fases muy tempranas si se quiere |
| Frontend (más adelante) | Next.js / React (open source) |
| IA (más adelante) | diferida; en TFG se puede mockear tools o usar cupo gratuito si hace falta |

Servicios de pago (APIs LLM, hosting, PSD2, etc.) **solo cuando el producto se use de verdad**. El motor debe poder desarrollarse y validarse 100 % offline.

---

## 17. Versionado

- `engine_version`: semver del paquete `financetwin_engine`
- Cambio de fórmula o de regla de redondeo que altere resultados → **MINOR/MAJOR** + nota en changelog del motor
- Los `calculation_run` guardan siempre la versión usada
- Tests golden fallan si un cambio altera resultados sin actualizar expected + changelog

---

## 18. Simplificaciones MVP (lista explícita)

1. Lag cobro/pago = `floor(días/30)` meses  
2. Sin saldos iniciales AR/AP (o cero) en v0.1  
3. Un único tipo de IVA  
4. IS mensual aproximado / modos de pago simplificados (sin compensación plena de bases negativas entre meses)  
5. Tipo de interés de préstamo constante (TIN/12)  
6. Sin inventario  
7. Patrimonio como residual de cuadre de balance (con chequeo de coherencia)  
8. VAN de proyecto sobre FCF before financing  
9. Sin multi-divisa  
10. Fee de apertura de préstamo: salida de caja simple en disposición  
11. Leasing: como coste (o loan simplificado), no norma contable completa  

Cualquier implementación debe poder devolver esta lista en `warnings` o `trace.simplifications_applied`.

---

## 19. Criterios de aceptación de esta spec

Se considera el motor v0.1 **conforme** cuando:

1. Existen tests automatizados para G1–G11 (o equivalentes numéricos fijados)
2. Pasan todos los invariantes §13 en un escenario demo de ≥ 24 meses
3. No hay `float` en rutas monetarias
4. `calculate()` es puro y determinista
5. Un escenario de “nueva tienda + préstamo” produce P&L, caja, VAN/TIR/payback y financing_need sin intervención manual de fórmulas fuera del motor
6. Carencia total distingue gasto financiero (P&L) de interés pagado (caja)
7. No hay doble conteo de CAPEX asset+investment

---

## 20. Fuera de alcance → docs vecinos

| Tema | Documento |
|---|---|
| Forma exacta ORM/JSON de entidades | `MODELO_DATOS.md` |
| Cómo un pack rellena el input | `DECISION_PACKS.md` |
| Validación con empresa real | `VALIDACION.md` |
| Sensibilidad / stress (orquestación) | misma librería analytics llamando a `calculate()` |
| Leasing como producto UX | `DECISION_PACKS.md` (pack comprar vs leasing) |

---

## 21. Changelog de la spec

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-03 | Primera spec normativa del motor MVP |
| 1.1 | 2026-10-03 | Auditoría: índice t=0..H-1; carencia total accrual vs pago; AR/AP; anti doble CAPEX; TIN/12; G2 real; G11; presupuesto 0; motivos de exclusión |

---

*Normativa: ante conflicto entre código y este documento, gana este documento hasta que se actualice conscientemente.*

### Nota de honestidad (post-auditoría)

Esta spec **no era perfecta en v1.0**. Los fallos corregidos en 1.1 eran de especificación (ambigüedad/error), no de “detalle menor”.  
Seguirá habiendo bordes al implementar: por eso existen golden tests e invariantes. “Perfecto” aquí significa **suficientemente cerrado para codificar sin inventar**, no infalible para siempre.
