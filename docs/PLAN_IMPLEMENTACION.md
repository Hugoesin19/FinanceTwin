# PLAN DE IMPLEMENTACIÓN — Norma anti-alucinación

**Finance Twin Implementation Plan**  
Versión: `1.0`  
Estado: **documento rector del desarrollo**  
Autoridad: este archivo manda el *orden* y las *reglas de trabajo*; las specs mandan el *contenido*.

---

## 0. Para qué existe este documento

Las specs (`PRODUCTO`, `MOTOR`, `MODELO`, `PACKS`, `VALIDACION`) dicen **qué** construir.  
Este documento dice **cómo trabajar al programar** para que:

- no se inventen requisitos
- no se salte el orden
- no se “complete” lo que la spec no dice
- cada paso tenga un criterio de hecho verificable

**Si al codear hay duda:** se mira la spec citada → si sigue habiendo duda → se pregunta al humano o se abre ADR. **Nunca se asume.**

---

## 1. Fuentes de verdad (prioridad)

| Prioridad | Documento | Manda sobre |
|---|---|---|
| 1 | `MOTOR_FINANCIERO.md` | Fórmulas, pipeline, golden, invariantes |
| 1 | `MODELO_DATOS.md` | Entidades, snapshot, mapper, enums |
| 1 | `DECISION_PACKS.md` | Inputs, build ops, packs |
| 1 | `VALIDACION.md` | Criterios PASS/FAIL, L0–L5 |
| 2 | `PRODUCTO.md` | Alcance de producto, qué está fuera |
| 2 | **Este plan** | Orden de fases y reglas de trabajo |
| 3 | ADR en `docs/adr/` | Decisiones puntuales no cubiertas |

**Conflictos:**
- Cálculo: gana `MOTOR_FINANCIERO`
- Forma de datos: gana `MODELO_DATOS`
- Packs: gana `DECISION_PACKS`
- Si dos specs chocan: **parar**, actualizar la spec (versión + changelog), luego codear

---

## 2. Reglas anti-alucinación (obligatorias)

### R1 — No inventar
Prohibido añadir:
- campos, enums, packs, endpoints, pantallas o fórmulas no escritas en specs
- “mejoras obvias” no pedidas (Monte Carlo, multi-divisa, agentes, etc.)

### R2 — No rellenar huecos con creatividad
Si falta un detalle en la spec:
1. Buscar en los 5 docs prioritarios  
2. Si no está → preguntar al usuario **o** crear ADR de 10–20 líneas + bump menor de la spec  
3. Prohibido: “lo dejo así por ahora” sin registrarlo

### R3 — Un solo camino de cálculo
Solo `financetwin_engine.calculate()`.  
UI, API e IA **no** recalculan VAN, cuotas ni caja.

### R4 — Decimal, no float
Ningún importe ni rate financiero en `float`.

### R5 — Tests antes de “seguir”
No se avanza de fase si la anterior no cumple su Definición de Hecho (DoD).

### R6 — Presupuesto 0 €
Sin servicios de pago en desarrollo. Stack local libre (Python, pytest, Postgres/SQLite local, etc.).

### R7 — Datos reales fuera de git
Cualquier dato de empresa piloto → gitignore / carpeta local. En repo solo fixtures sintéticas.

### R8 — Commits con trazabilidad
Cada cambio relevante cita la fase (`F0`, `F1`…) y la spec tocada.  
Ejemplo mensaje: `engine(F1): French loan schedule per MOTOR §7.5`

### R9 — Alcance MVP = won’t de PRODUCTO
Lo listado en PRODUCTO §25.4 y exclusiones del motor **no se implementa** “de paso”.

### R10 — La IA (Cursor) es operario, no arquitecto
Al pedir implementación: este plan + la spec de la fase activa.  
Si el agente propone algo fuera de fase → rechazar.

---

## 3. Definición de Hecho (plantilla)

Una fase está **HECHA** solo si:

1. Código en la ruta prevista  
2. Tests automatizados del DoD en verde  
3. No hay TODOs silenciosos que cambien el comportamiento  
4. Si hubo decisión nueva → ADR o changelog de spec  
5. `DOCUMENTACION.md` / este plan actualizan el estado de la fase  

---

## 4. Fases de implementación (orden fijo)

No reordenar. No fusionar fases “para ir más rápido” sin acuerdo explícito.

---

### F0 — Scaffold del repo de código

**Objetivo:** poder ejecutar tests.

**Hacer:**
- Carpeta `engine/` con paquete `financetwin_engine`
- `pyproject.toml` o `requirements.txt` (pytest, sin deps de pago)
- `engine/tests/` vacío estructurado (`unit/`, `golden/`, `invariants/`)
- `README` del engine: cómo correr `pytest`
- Versión `engine_version = 0.1.0`

**No hacer:** API, web, IA, BD.

**Spec:** PRODUCTO §21.2 (estructura), este plan.

**DoD:**
- [x] `pytest` se ejecuta (aunque sea 1 test smoke `test_version`)
- [x] paquete importable: `from financetwin_engine import __version__`

**Estado:** `HECHA`

---

### F1 — Motor L0 núcleo (sin packs)

**Objetivo:** motor conforme a VALIDACION L0 parcial → completo.

**Orden interno obligatorio:**

| Paso | Entrega | Spec | Tests | Estado |
|---|---|---|---|---|
| F1.1 | Tipos Decimal + `InvestmentMetrics` (VAN, TIR, payback) | MOTOR §10, §14 G1–G2 | G1, G2 | HECHA |
| F1.2 | `build_loan_schedule` francés/lineal/bullet + carencias | MOTOR §7.5, G3–G5 | G3, G4, G5 | HECHA |
| F1.3 | P&L mensual básico | MOTOR §7.1–7.4, G6, G9 | G6, G9 | HECHA |
| F1.4 | Caja + lags + AR/AP simplificado | MOTOR §8, G7, G8 | G7, G8 | HECHA |
| F1.5 | CAPEX / anti-doble | MOTOR §8.2, G11 | G11 | HECHA |
| F1.6 | `calculate()` pipeline + invariantes + hash + G10 | MOTOR §6, §13, G10 | invariantes + G10 | HECHA |
| F1.7 | Impuestos simplificados + policies + financing_need | MOTOR §9, §11–12 | tests dedicados | HECHA |

**No hacer en F1:** mapper JSON snapshot, packs, FastAPI, UI.

**DoD:**
- [x] G1–G11 PASS
- [x] Invariantes PASS en fixture demo ≥ 24 meses
- [x] Cero `float` en rutas monetarias
- [x] `calculate()` puro (sin I/O)

**Estado:** `HECHA`

---

### F2 — Modelo + mapper (L1)

**Objetivo:** `CompanyTwinSnapshot` → `CalculationInput`.

**Hacer:**
- Schemas Pydantic (o equivalente) según MODELO §5–6
- `months_between`, `apply_build_ops`, `to_calculation_input`
- Tests M1–M7 de VALIDACION §4

**No hacer:** persistencia real obligatoria (puede ser in-memory); packs completos.

**DoD:**
- [x] VALIDACION L1 PASS
- [x] Fixture “tienda + préstamo” produce input aceptado por `calculate()`

**Estado:** `HECHA`

---

### F3 — Pack `new_site` E2E (L2)

**Objetivo:** una decisión real del producto funciona de punta a punta **en librería** (sin UI).

**Hacer:**
- Implementar solo pack `new_site` según DECISION_PACKS §5
- `build` → variantes base/conservative/adverse
- Análisis mínimo: policy checks + inverse sensitivity stubs o reales según motor analytics (si analytics no está, al menos policy + metrics del calculate)
- Test E2E VALIDACION §5.2

**No hacer:** los otros 5 packs (salvo helpers compartidos); chat IA.

**DoD:**
- [x] E2E new_site PASS (VALIDACION §5.2)
- [x] No muta ModelVersion “current” persistido
- [x] Funding insuficiente → ERROR

**Estado:** `HECHA`

---

### F4 — Resto de packs MVP

**Orden:** `financing` → `asset_purchase` → `hiring` → `generic_investment` → `liquidity_plan`

**DoD por pack:**
- [x] inputs_schema + validate + build + actual_keys
- [x] ≥ 1 test de build + calculate
- [x] Cumple DECISION_PACKS (ahorros §2.5, leasing, etc.)

**Estado:** `HECHA`

---

### F5 — Persistencia mínima + API mínima

**Objetivo:** guardar company/snapshot/scenario/calculation_run y exponer calculate.

**Hacer:**
- BD local (SQLite aceptable; Postgres local preferible si ya está)
- Tablas mínimas según MODELO (Company, ModelVersion, Scenario, CalculationRun)
- API FastAPI: health + create company + put snapshot + run scenario
- Spec de endpoints: si no existe `API.md`, crear **solo los endpoints implementados** (no inventar catálogo completo)

**No hacer:** auth compleja, multi-tenant cloud, PSD2.

**DoD:**
- [x] Flujo new_site vía API con persistencia de CalculationRun
- [x] Resultados Decimal serializados como string

**Estado:** `HECHA`

**Entregables:**
- `api/financetwin_api/` — SQLite Store + FastAPI (`create_app`)
- Endpoints: health, companies, snapshot GET/PUT, new_site/run, calculation-runs/{id}
- `docs/API.md` — solo endpoints reales
- Tests E2E: `api/tests/test_api_new_site_flow.py` (8 passed)
- Auditoría 1.5.1: parent_id, índice único current, Decimal-safe JSON overrides

---

### F6 — UI mínima Decision Studio

**Objetivo:** un humano no técnico puede lanzar `new_site` y ver informe.

**Hacer:**
- Pantallas mínimas: cargar/editar twin simple, formulario pack, resultado (métricas + caja + políticas)
- Sin diseño ornamental; datos del CalculationRun

**No hacer:** chat IA, dashboards completos, Advisor workspace.

**DoD:**
- [x] Camino feliz new_site usable en local
- [x] Ningún número en UI que no venga del motor

**Estado:** `HECHA`

**Entregables:**
- UI estática same-origin: `api/financetwin_api/static/` (`/`, `/static/*`)
- Flujo: crear empresa → twin → form `new_site` → informe (métricas + caja + políticas)
- `docs/ARQUITECTURA.md` — capas reales F0–F6
- Tests: `api/tests/test_ui_f6.py`
- Auditoría 1.6.1: restore session + hidratar twin; informe se limpia en error; GET snapshot distingue company/no-snapshot; golden NPV UI; busy-state

---

### F7 — Decision History + plan vs real (Twin Loop básico)

**Hacer:**
- Entidades Decision, ActualResult, BiasProfile
- Registro de decisión post-escenario
- Calibración §2.6 packs si n≥3

**DoD:**
- [x] V5 automatizable con fixture
- [x] Calibración ofrece escenario solo con n≥3

**Estado:** `HECHA`

**Entregables:**
- Engine: `analytics/bias.py` (deviation, mediana, calibrate §2.6, gate n≥3)
- BD: `decision`, `decision_milestone`, `actual_result`, `bias_profile`
- API: register decision, status, actuals, bias-profiles, calibration/preview
- Tests: `engine/tests/unit/test_f7_bias.py` + `api/tests/test_f7_twin_loop.py`
- Auditoría 1.7.1: n=decisiones (no periodos); keys/packs/status canónicos; mapping calibración por pack; forecast=0 warning

---

### F8 — Validación empírica TFG (L3–L4)

**Hacer:** ejecutar protocolo VALIDACION V1–V6 con datos piloto o plan B.  
**No es “feature”:** es campaña de evidencia.

**DoD:** criterios §10 de VALIDACION.

**Estado:** `PENDIENTE`

---

### F9 — IA opcional (L5)

**Solo después de F6+.**  
Orquestador con tools tipadas; nunca calcula.  
V7 según VALIDACION.

**Estado:** `DIFERIDA`

---

## 5. Checklist MVP de producto (must)

Marcar solo cuando la fase correspondiente esté HECHA.

| Must (PRODUCTO / packs) | Fase | Hecho |
|---|---|---|
| Motor P&L + caja + deuda + VAN/TIR | F1 | [x] |
| Trazabilidad / hash / version | F1 | [x] |
| Snapshot + mapper | F2 | [x] |
| Pack new_site | F3 | [x] |
| Packs restantes MVP | F4 | [x] |
| Persistencia + API mínima | F5 | [x] |
| UI mínima | F6 | [x] |
| Twin Loop / History | F7 | [x] |
| Evidencia validación TFG | F8 | [ ] |

Should/could de PRODUCTO: **fuera** hasta cerrar esta tabla.

---

## 6. Protocolo de una sesión de programación

Antes de escribir código:

1. Leer **este plan** → fase activa  
2. Leer la sección de spec citada en esa fase  
3. Listar archivos que se tocarán  
4. Escribir/ajustar tests del DoD primero (o junto)  
5. Implementar hasta verde  
6. Actualizar estado de fase aquí (`PENDIENTE` → `HECHA`)  
7. Si surgió decisión: ADR

**Prompt tipo para el agente (copiar/pegar):**

> Implementa solo la fase Fx.y del `PLAN_IMPLEMENTACION.md`.  
> Spec vinculante: [archivo §…].  
> No implementes nada fuera de esa fase.  
> Si falta un detalle en la spec, pregunta; no inventes.  
> DoD: [copiar checklist].

---

## 7. ADRs

Ruta: `docs/adr/NNNN-titulo-corto.md`

Usar cuando:
- hay dos opciones técnicas válidas
- hay que ampliar una spec
- se descubre un bug de spec

Plantilla mínima:

```text
# ADR NNNN — Título
Fecha:
Estado: accepted | rejected | superseded
Contexto:
Decisión:
Alternativas:
Consecuencias:
Specs a actualizar:
```

---

## 8. Qué hacer si “falta un documento”

| Necesidad | Acción |
|---|---|
| Endpoint no especificado | Crear `API.md` **solo** con lo implementado en F5, o sección en este plan |
| Estructura de carpetas web | Documentar en ADR o `ARQUITECTURA.md` **al cerrar F5/F6**, no antes |
| Prompt IA | `IA_TOOLS.md` solo en F9 |

No bloquear F1 por no tener `ARQUITECTURA.md` completo.

---

## 9. Estado global del plan

| Fase | Nombre | Estado |
|---|---|---|
| F0 | Scaffold | HECHA |
| F1 | Motor L0 | HECHA |
| F2 | Mapper | HECHA |
| F3 | Pack new_site | HECHA |
| F4 | Resto packs | HECHA |
| F5 | API + BD | HECHA |
| F6 | UI mínima | HECHA |
| F7 | Twin Loop | HECHA |
| F8 | Validación TFG | PENDIENTE |
| F9 | IA | DIFERIDA |

**Fase activa actual:** `F8`

---

## 10. Changelog

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-10-03 | Plan rector anti-alucinación + fases F0–F9 |
| 1.0.1 | 2026-10-03 | F0 HECHA (scaffold `engine/` + pytest smoke); fase activa → F1 |
| 1.0.2 | 2026-10-03 | F1.1 HECHA (Decimal + VAN/TIR/payback + G1/G2); fase activa → F1.2 |
| 1.0.3 | 2026-10-03 | F1.2 HECHA (loan schedule G3–G5); fase activa → F1.3 |
| 1.0.4 | 2026-10-03 | F1.3 HECHA (P&L G6/G9); fase activa → F1.4 |
| 1.0.5 | 2026-10-03 | F1.4 HECHA (caja G7/G8); fase activa → F1.5 |
| 1.1 | 2026-10-03 | F1 HECHA (F1.1–F1.7, G1–G11, invariantes, calculate); fase activa → F2 |
| 1.1.1 | 2026-10-03 | Auditoría F1: fix doble CAPEX one_off en caja; +10 tests regresión (linear/bullet/TIR/G11 E2E) |
| 1.2 | 2026-10-03 | F2 HECHA (mapper snapshot→CalculationInput, M1–M7); fase activa → F3 |
| 1.2.1 | 2026-10-03 | Auditoría F2: ADR0001 skip_drawdown; dedupe own_funds; +tests BuildOp/invariantes |
| 1.3 | 2026-10-03 | F3 HECHA (pack new_site E2E + funding ERROR); fase activa → F4 |
| 1.3.1 | 2026-10-03 | Auditoría F3: IDs deterministas; opex% en variantes; analysis_plan; +8 tests |
| 1.4 | 2026-10-03 | F4 HECHA (5 packs MVP + tests; IRR overflow harden); fase activa → F5 |
| 1.4.1 | 2026-10-03 | Auditoría F4: actual_keys financing; CAPEX en variantes asset; +9 tests |
| 1.5 | 2026-10-03 | F5 HECHA (SQLite + FastAPI + API.md; new_site run persiste CalculationRun; Decimals string); fase activa → F6 |
| 1.5.1 | 2026-10-03 | Auditoría F5: parent_id en ModelVersion; índice único is_current; overrides/JSON Decimal-safe; calc sin round-trip BuildOp; +4 tests |
| 1.6 | 2026-10-03 | F6 HECHA (UI mínima Decision Studio same-origin; ARQUITECTURA.md; métricas = campos motor); fase activa → F7 |
| 1.6.1 | 2026-10-03 | Auditoría F6: restore/hidratar twin; clear report on error; snapshot 404 company vs empty; golden NPV; +tests |
| 1.7 | 2026-10-03 | F7 HECHA (Decision/ActualResult/BiasProfile; V5 fixture; calibración solo n≥3); fase activa → F8 |
| 1.7.1 | 2026-10-03 | Auditoría F7: n=decisiones; catálogo variable_key/pack/status; pack mapping calibración; +tests edge |

---

*Norma: programar sin este plan abierto = riesgo de alucinación de alcance. La fase activa es la única licencia para escribir código.*
