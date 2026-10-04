# VALIDACIÓN — Protocolo

**Finance Twin Validation Protocol**  
Versión de spec: `1.0`  
Estado: lista para ejecutar cuando exista implementación + datos  
Referencias: [`PRODUCTO.md`](PRODUCTO.md) §23, §27 · [`MOTOR_FINANCIERO.md`](MOTOR_FINANCIERO.md) §13–14 · [`MODELO_DATOS.md`](MODELO_DATOS.md) · [`DECISION_PACKS.md`](DECISION_PACKS.md)

---

## 0. Propósito

Este documento define **cómo sabemos que el sistema está bien** — con métodos, métricas, umbrales y evidencias.

- Si un criterio de “éxito” no está aquí, **no se afirma** en la memoria del TFG ni en demos.
- Separa validación **técnica** (automatizable) de validación **empírica** (empresa / usuarios).
- Presupuesto 0 €: tests locales (`pytest`), Excel/CSV de referencia, sin SaaS de pago obligatorio.

---

## 1. Qué NO se valida (explícito)

| Afirmación prohibida | Motivo |
|---|---|
| “Finance Twin mejora las decisiones empresariales” | Requiere diseño experimental causal, N grande y tiempo |
| “La IA predice mejor que un humano” | Fuera de alcance; la IA no calcula |
| “El modelo fiscal es exacto ante Hacienda” | IS/IVA son simplificaciones declaradas |
| “Monte Carlo da la probabilidad real de éxito” | Ni siquiera está en MVP |

La validación demuestra: **fidelidad de cálculo, utilidad del proceso y coherencia plan–real**, no superioridad causal.

---

## 2. Capas de validación

```text
L0  Invariantes + golden del motor          (CI / pytest)     OBLIGATORIO
L1  Mapper snapshot → CalculationInput      (tests unidad)    OBLIGATORIO
L2  Decision Packs build → motor            (tests integración) OBLIGATORIO
L3  V1–V5 empíricas con datos reales/sintéticos               OBLIGATORIO TFG
L4  V6 utilidad percibida                                     OBLIGATORIO TFG (mín. 1 sesión)
L5  V7 capa IA                                                CUANDO exista IA; si no, N/A documentado
```

**Regla de avance:** no se considera “motor conforme” sin L0.  
No se defiende el TFG sin L0 + L3 (al menos V1 y V3) + evidencia L4.

---

## 3. L0 — Motor: invariantes y golden

### 3.1 Invariantes

Ejecutar en **todo** `CalculationResult` de test (y en demo ≥ 24 meses):

Ver lista normativa en `MOTOR_FINANCIERO.md` §13.

**Umbral:** tolerancia monetaria `≤ 0.01 €` por igualdad de caja; balance `≤ 0.05 €`, salvo test que declare otra.

**Resultado:** PASS si 100 % de invariantes en la batería; FAIL si uno falla sin ADR + cambio de spec.

### 3.2 Casos golden G1–G11

Fuente: `MOTOR_FINANCIERO.md` §14.

| ID | Qué prueba | Criterio PASS |
|---|---|---|
| G1 | VAN r=0, payback | valores exactos de la spec |
| G2 | VAN con descuento | `18.22` (ROUND_HALF_UP 2 dec) |
| G3 | Francés | interés t0, D_final=0, Σ principal = P |
| G4 | Carencia capital | solo intereses en gracia; luego amortiza |
| G5 | Carencia total | P&L con gasto; caja interés 0; capitaliza |
| G6 | P&L simple | ebitda=net_income=1000 |
| G7 | Lag cobro + AR | collections y AR según spec |
| G8 | Shortfall | first_shortfall y max_shortfall |
| G9 | Amortización lineal | 100×12 |
| G10 | Determinismo | mismo hash/resultados |
| G11 | Anti doble CAPEX | capex_paid una sola vez |

**Ubicación de fixtures (cuando exista código):**  
`engine/tests/golden/*.json` — inputs + expected.

**PASS L0:** G1–G11 verdes + invariantes en escenario demo 24–36 meses.

---

## 4. L1 — Mapper de datos

### 4.1 Tests unitarios mínimos

| ID | Caso | PASS |
|---|---|---|
| M1 | `months_between` ejemplos de MODELO §11.1 | exacto |
| M2 | entidad con start < anchor activa → start_t=0 | |
| M3 | entidad end < anchor → excluida | |
| M4 | `grace_type=none` no se envía `none` al motor | |
| M5 | own_funds → un solo equity_injection implícito | |
| M6 | asset.investment_id ↔ linked_asset_ids | rechazo si incoherente |
| M7 | mismo snapshot+scenario → mismo `inputs_hash` | |

### 4.2 Schema

Validar `CompanyTwinSnapshot` con schema JSON/Pydantic (`schema_version=1.0`).  
**PASS:** reject de snapshots inválidos; accept de fixture mínima “tienda + préstamo”.

---

## 5. L2 — Decision Packs

### 5.1 Por cada pack MVP

| Check | PASS |
|---|---|
| `validate_inputs` rechaza funding insuficiente (`new_site`) | error, no warning |
| `build` no persiste cambio en ModelVersion current | |
| Variantes base/conservative/adverse generadas | 3 CalculationInput distintos |
| `actual_keys` ⊆ catálogo MODELO §14 | |
| Sin CostItem con amount &lt; 0 | |
| Leasing no fuerza VAN de compra | |

### 5.2 Caso canónico E2E (obligatorio)

**Pack:** `new_site`  
**Narrativa:** apertura con CAPEX 350k, ventas 40k/mes, deuda 200k, equity 150k (como en PRODUCTO).

**PASS:**
1. BuildOps válidos  
2. `calculate()` sin excepción  
3. Existen VAN, TIR o undefined documentado, payback o null, min_cash, financing_need  
4. Policy checks array presente  
5. Invariantes L0 OK  

No se exige que el VAN coincida con el ejemplo ilustrativo del PDF Madagascar (era ficticio).

---

## 6. L3 — Validación empírica V1–V5

### 6.1 Datos

**Preferente:** empresa piloto (p. ej. Madagascar) con 24–36 meses de histórico.  
**Plan B:** dataset sintético realista + 1 préstamo real anonimizado / cuadro bancario; declarar limitaciones.

Datos mínimos:

| Dataset | Contenido |
|---|---|
| `hist_pnl` | P&L mensual o trimestral real |
| `hist_cash` | saldos de caja fin de mes (o proxy bancario) |
| `loan_schedule_bank` | al menos 1 cuadro real |
| `decisions_past` | 3–5 decisiones con hipótesis recordadas y resultado |

Almacenamiento: **fuera de git** si son datos reales (como `docs/madagascar/`); en repo solo fixtures sintéticas anonimizadas.

---

### V1 — Fidelidad histórica del modelo

**Pregunta:** ¿El twin reproduce la situación financiera histórica?

**Método:**
1. Cargar histórico en snapshot (ingresos/costes/deuda/caja inicial del primer mes).  
2. Ejecutar motor en modo “reconstrucción” horizonte = N meses históricos **sin** decisiones nuevas.  
3. Comparar partidas clave mes a mes (o trimestre si el real es trimestral).

**Partidas mínimas:** revenue, ebitda (o proxy), closing_cash, debt_balance.

**Métricas:**

```text
APE_t = |pred_t - real_t| / max(|real_t|, ε)
MAPE = mean(APE_t)
Bias = mean((pred - real) / max(|real|, ε))
```

`ε = 1.00 €` para evitar división por 0.

**Umbrales PASS (declarados para TFG):**

| Partida | MAPE máximo | Notas |
|---|---|---|
| revenue | ≤ 10 % | si el modelo se alimentó de esas ventas, debe ser ≤ 5 %; 10 % si hay agregación |
| closing_cash | ≤ 15 % | más holgura por lags/IVA simplificados |
| debt_balance | ≤ 5 % | |

**FAIL controlado:** si se incumple, documentar *qué simplificación* lo explica (IVA, AR inicial=0, etc.), no ocultarlo.

**Evidencia:** tabla por mes + gráfico; anexo en memoria.

---

### V2 — Proyección (backtest)

**Pregunta:** ¿Proyecta caja de forma razonable bajo hipótesis conocidas a priori?

**Método:**
1. Ancla en T0 = hace 12 meses.  
2. Construir snapshot solo con info disponible entonces (no mirar el futuro).  
3. Proyectar H=12.  
4. Comparar closing_cash predicho vs real.

**Métricas:**
- MAPE de closing_cash (12 puntos)  
- Acierto del mes de caja mínima: `|t_pred - t_real| ≤ 2` meses  
- Señal de shortfall: si real rompe política, el modelo ¿lo señalaba? (sí/no + lead time)

**Umbrales PASS:**

| Métrica | PASS |
|---|---|
| MAPE caja | ≤ 25 % |
| Mes de mínimo | ≤ 2 meses de error |
| Dirección de tensión | si hubo shortfall real, modelo lo marca en ±2 meses o documenta por qué no |

Holgura mayor que V1 porque es predicción, no reconstrucción.

---

### V3 — Instrumentos (préstamo / activo / VAN-TIR)

**Pregunta:** ¿Los instrumentos financieros están bien calculados?

**Método A — Préstamo:**
1. Introducir condiciones del cuadro bancario.  
2. Comparar cuota, intereses y vivo mes a mes (o al menos 12 meses).

**PASS préstamo:**  
- `|cuota_modelo - cuota_banco| ≤ 0.05 €` (tras redondeo) en ≥ 11/12 meses, **o**  
- error relativo medio de interés ≤ 1 % si el banco usa convención distinta (documentar TIN vs TAE).

**Método B — VAN/TIR:**
1. Serie FC conocida.  
2. Comparar con Excel/`numpy-financial` / cálculo manual independiente.

**PASS:** VAN a 2 decimales igual; TIR anual diferencia ≤ 1e-6 en fracción (o 0.0001 %).

**Método C — Activo lineal:** caso G9 + un activo real si existe.

---

### V4 — Reconstrucción de decisiones

**Pregunta:** ¿Decisiones pasadas se pueden expresar como packs/escenarios?

**Método:**
1. Elegir 3–5 decisiones reales (idealmente tipadas a packs).  
2. Entrevista breve: hipótesis que usaron entonces.  
3. Construir pack + scenario con esos inputs.  
4. Checklist de representación.

**PASS por decisión (scorecard 0–1):**

| Criterio | Peso |
|---|---|
| Pack correcto o “generic_investment” justificado | 0.2 |
| CAPEX/timing representados | 0.2 |
| Funding representado | 0.2 |
| Efecto operativo (ventas/costes/personal) representado o declarado fuera de alcance | 0.2 |
| Informe comprensible para el decisor | 0.2 |

**PASS V4:** media ≥ 0.8 en ≥ 3 decisiones.

---

### V5 — Desviaciones plan vs real

**Pregunta:** ¿El sistema cuantifica bien forecast vs actual?

**Método:**
1. Sobre decisiones V4 con resultado conocido.  
2. Registrar `ActualResult` para keys del pack.  
3. Comprobar `deviation_pct` = `(forecast-actual)/forecast`.  
4. Si n≥3, BiasProfile mediana coherente con las desviaciones.

**PASS:**
- Fórmula deviation exacta (± 1e-9 relativa)  
- Signo correcto (sobre/infra estimación)  
- BiasProfile.median_bias = mediana de las desviaciones de esa key  

No se exige aún que la calibración “mejore” decisiones futuras (eso sería longitudinal).

---

## 7. L4 — V6 Utilidad percibida

**Pregunta:** ¿El proceso se entiende y se percibe útil?

**Método:** sesión 45–90 min con gerente (y opcionalmente asesor).

### 7.1 Protocolo de sesión

1. Mostrar situación twin (5–10 min)  
2. Simular 1 decisión real con un pack (20–40 min)  
3. Revisar informe + “qué tendría que pasar” (10–15 min)  
4. Cuestionario (5–10 min)

### 7.2 Cuestionario (Likert 1–5)

| ID | Ítem |
|---|---|
| U1 | Entendí los resultados sin ser experto financiero |
| U2 | El informe me ayuda más que un Excel suelto para esta decisión |
| U3 | Confío en que los números no los inventa la IA |
| U4 | La pregunta “qué tendría que pasar” aporta valor |
| U5 | Volvería a usar esto en otra decisión importante |
| U6 | Se lo recomendaría a otra pyme similar |

Preguntas abiertas: qué faltó, qué sobró, qué decisión simularían después.

### 7.3 PASS V6 (mínimo TFG)

- ≥ 1 sesión documentada (acta + respuestas)  
- Media U1–U6 ≥ 3.5 / 5  
- U3 ≥ 4 (confianza en separación IA/motor) — si no, es hallazgo crítico a discutir  

No se exige significación estadística.

---

## 8. L5 — V7 Capa de IA (cuando exista)

Si la IA **aún no está implementada**, marcar V7 como `N/A — diferida` en la memoria (no es FAIL del motor).

Cuando exista:

### 8.1 Clasificación de packs

Batería ≥ 30 frases (5 por pack) → pack esperado.  
**PASS:** accuracy ≥ 85 %; errores solo a packs “cercanos” documentados.

### 8.2 No invención de cifras

Para ≥ 20 informes generados:
- Extraer números del texto  
- Verificar igualdad con `CalculationResult`  
**PASS:** 100 % de cifras citadas coinciden; si el modelo redondea distinto en prosa → FAIL.

### 8.3 No rellenar huecos

Prompts con datos faltantes → debe preguntar / marcar unknown, no estimar VAN.  
**PASS:** 10/10 casos.

---

## 9. Matriz de evidencias (para la memoria TFG)

| ID | Evidencia a archivar | Estado inicial |
|---|---|---|
| L0 | Log pytest G1–G11 + invariantes | PASS (ver `validation/results/F8_RESUMEN.md`) |
| L1 | Tests mapper | PASS |
| L2 | E2E new_site | PASS |
| V1 | Tablas MAPE histórico | PASS* Plan B (`validation/results/v1_mape.json`) |
| V2 | Backtest 12m | PASS* Plan B débil (`v2_backtest.json`) |
| V3 | Diff cuadro préstamo + VAN independiente | PASS (`v3_loan_diff.json`) |
| V4 | Scorecards 3–5 decisiones | PASS* packs ejecutados (`v4_scorecards.json`); entrevista real pendiente |
| V5 | ActualResult + BiasProfile | PASS |
| V6 | Acta sesión + Likert | PENDIENTE (plantilla lista) |
| V7 | N/A o batería IA | N/A — F9 diferida |

Carpeta sugerida local (gitignored si hay datos reales):  
`validation/` con subcarpetas `fixtures/`, `results/`, `sessions/`.

---

## 10. Criterios globales de “listo para defender”

El trabajo se considera **validado para defensa TFG** si:

1. **L0 PASS**  
2. **L2** caso `new_site` PASS  
3. **V1 PASS** o FAIL documentado con causa de simplificación + plan de mejora  
4. **V3 PASS** (al menos préstamo **o** VAN/TIR independiente; ideal ambos)  
5. **V4** media ≥ 0.8 en ≥ 3 decisiones **o** plan B sintético + 1 decisión real  
6. **V6** sesión + media Likert ≥ 3.5 y U3 ≥ 4  
7. Limitaciones (IVA, AR=0, etc.) listadas en un apartado fijo de la memoria  

V2 y V5 refuerzan nota; si faltan datos, declarar cobertura parcial.

---

## 11. Plan B (sin empresa piloto)

Si no hay Madagascar u otra pyme:

| Pieza | Sustituto |
|---|---|
| V1–V2 | Serie sintética generada por el propio motor + ruido controlado + “reconstrucción” (menos potente; declararlo) |
| V3 | Cuadros públicos / Excel bancario genérico + golden |
| V4–V5 | 3 decisiones ficticias pero coherentes + 1 entrevista a empresario sin ceder datos |
| V6 | Sesión con empresario usando datos sintéticos o anonimizados |

El TFG sigue siendo defendible si se es **honesto** con el plan B.

---

## 12. Relación con CI / desarrollo

```text
commit → pytest L0 (+ L1 si aplica) debe pasar
no merge de motor si G* fallan
cambios de fórmula → bump engine_version + actualizar golden expected + nota changelog MOTOR
```

Presupuesto 0: GitHub Actions opcional; como mínimo pytest local antes de commit.

---

## 13. Glosario rápido de métricas

| Métrica | Definición |
|---|---|
| APE | error porcentual absoluto de un punto |
| MAPE | media de APE |
| Bias | media del error relativo con signo |
| DSCR | ver motor |
| deviation_pct | `(forecast - actual) / forecast` |

---

## 14. Changelog

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-03 | Protocolo L0–L5, V1–V7, umbrales, plan B, evidencias TFG |

---

*Normativa de validación: no se afirman resultados fuera de estos criterios.*
