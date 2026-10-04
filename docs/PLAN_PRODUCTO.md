# PLAN DE PRODUCTO — Continuación post-fundación

**Finance Twin Product Plan (UI + usabilidad)**  
Versión: `1.0`  
Estado: **documento rector del desarrollo de producto usable**  
Precedente: [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md) (F0–F8 **cerradas**; F9 IA **diferida**)

---

## 0. Para qué existe

`PLAN_IMPLEMENTACION.md` construyó el **núcleo** (motor, packs, API, UI mínima, Twin Loop, evidencia Plan B).

Este documento define **los siguientes pasos de producto** para que una persona no técnica pueda:

1. Cargar/editar un twin  
2. Lanzar **los 6 packs MVP**  
3. Ver un informe defendible  
4. Registrar decisión y plan vs real  
5. (Luego) importar datos por plantilla  

**No** incluye chat/IA de pago (eso sigue siendo F9 diferida).

**Si al codear hay duda:** spec citada → si sigue duda → preguntar o ADR. **Nunca inventar.**

---

## 1. Fuentes de verdad (igual que el plan F0–F8)

| Prioridad | Documento | Manda sobre |
|---|---|---|
| 1 | `MOTOR_FINANCIERO.md` | Cálculo |
| 1 | `MODELO_DATOS.md` | Entidades / snapshot |
| 1 | `DECISION_PACKS.md` | Packs e inputs |
| 1 | `API.md` | Solo endpoints **ya implementados** |
| 2 | `PRODUCTO.md` | Alcance MVP / won’t-have (§25) |
| 2 | **Este plan** | Orden de fases P1+ |
| 2 | `PLAN_IMPLEMENTACION.md` | Reglas R1–R10 (siguen vigentes) |
| 3 | `ARQUITECTURA.md` | Capas reales; actualizar al cerrar fases UI |
| 3 | ADR | Decisiones nuevas |

Las reglas **R1–R10** de `PLAN_IMPLEMENTACION.md` §2 aplican sin cambio (Decimal, un solo motor, €0, no inventar, etc.).

---

## 2. Estado de partida (no rehacer)

| Capa | Estado |
|---|---|
| Motor + golden L0 | HECHO |
| Mapper + 6 packs | HECHO (librería) |
| API new_site + Twin Loop | HECHO |
| UI | Solo twin + **new_site** + informe mínimo |
| Import Excel/CSV | NO |
| Chat / IA (F9) | DIFERIDA (puede costar API LLM) |

---

## 3. Principios específicos de esta etapa

### P-R1 — UI no calcula
Todos los números en pantalla salen de `CalculationRun` / respuesta API. Cero fórmulas financieras en JS.

### P-R2 — API primero si falta contrato
Si la UI necesita un endpoint que no está en `API.md` → implementarlo en la **misma fase** (o subtarea DoD) y **actualizar `API.md` solo con lo real**.

### P-R3 — Un pack = mismo patrón UX
Formulario (inputs del pack) → variante → run → informe. No inventar wizards distintos por pack sin ADR.

### P-R4 — Sin Node obligatorio
Seguir stack €0: UI estática same-origin (`api/.../static`) salvo ADR que justifique otra cosa.

### P-R5 — F9 fuera de alcance
Prohibido meter orquestador LLM “de paso”. Si se quiere IA → reactivar F9 con plan propio + coste explícito.

---

## 4. Fases de producto (orden fijo)

No reordenar sin acuerdo explícito.

---

### P1 — API: ejecutar cualquier pack MVP

**Objetivo:** la UI (y tests) pueden lanzar los 6 packs, no solo `new_site`.

**Hacer:**
- Endpoint genérico p. ej. `POST /companies/{id}/packs/{pack_id}/run`  
  Packs: `new_site | financing | asset_purchase | hiring | generic_investment | liquidity_plan`
- Reutilizar packs del engine; misma persistencia Scenario + CalculationRun que F5
- Mantener `new_site/run` como alias o deprecar documentado (ADR si se elimina)
- Validación de `pack_id` y errores 400 con issues del pack

**No hacer:** auth, multi-tenant, PDF, chat.

**Spec:** DECISION_PACKS · MODELO §7 · API.md (actualizar) · PRODUCTO §25 packs.

**DoD:**
- [x] Los 6 packs corren vía API con fixture mínima
- [x] Decimals string; no mutan ModelVersion current
- [x] `API.md` actualizado; tests E2E ≥ 1 por pack (o parametrizado)

**Estado:** `HECHA`

---

### P2 — Decision Studio UI: 6 packs

**Objetivo:** humano no técnico elige pack, rellena inputs, ve resultado.

**Hacer:**
- Selector de pack en la UI
- Formularios por pack (campos = `inputs_schema` / DECISION_PACKS; defaults visibles)
- Variante `base | conservative | adverse`
- Reutilizar bloque de informe (métricas + políticas + caja + trazabilidad)
- Solo campos del motor (como F6)

**No hacer:** Home completo, dashboards, PDF, chat.

**Spec:** PRODUCTO §13 / §19 Decision Studio · DECISION_PACKS · este plan P1.

**DoD:**
- [x] Camino feliz local de los 6 packs desde el navegador
- [x] Ningún número inventado en JS
- [x] Tests smoke: HTML/JS referencian packs canónicos + API genérica

**Estado:** `HECHA`

---

### P3 — Informe usable (lectura humana)

**Objetivo:** el resultado se entiende sin mirar JSON crudo.

**Hacer:**
- Resumen ejecutivo fijo: VAN, TIR, payback, caja mínima, shortfall, políticas fail/pass
- Tabla de caja legible (meses; columnas canónicas del motor)
- Bloque “Trazabilidad” (run_id, hashes, engine_version) siempre visible
- Comparar 2–3 variantes del mismo run-set (base/conservative/adverse) **solo** con datos devueltos por el motor (3 llamadas API, no promedios caseros)

**No hacer:** PDF banco, marca blanca, gráficos fancy obligatorios.

**Spec:** PRODUCTO informe ejecutivo (estructura) · MOTOR métricas · API results.

**DoD:**
- [x] Usuario ve comparación de variantes sin abrir DevTools
- [x] Textos de informe mapean 1:1 a campos del CalculationResult
- [x] Test o checklist documentado de campos mostrados ⊆ respuesta API

**Estado:** `HECHA`

---

### P4 — Twin Loop en UI (History básico)

**Objetivo:** cerrar el bucle decisión → real → sesgo sin salir del navegador.

**Hacer:**
- Tras un run: “Registrar decisión” (status approved/executed + rationale)
- Listar decisiones de la empresa (endpoint list si falta → añadirlo y documentar)
- Formulario ActualResult (keys del catálogo MODELO §14 / `actual_keys` del pack)
- Vista BiasProfile + botón “Preview calibración” (solo si API dice `offered=true`)

**No hacer:** Advisor multi-empresa, soft-delete, reabrir executed.

**Spec:** MODELO §8 · DECISION_PACKS §2.6 / §11 · API Twin Loop (F7) · UI.

**DoD:**
- [x] Flujo UI: run → register → actuals → bias n≥3 → calibration preview
- [x] Rechazo visible si n&lt;3 (no ofrecer calibración en UI)
- [x] Tests API list (si nuevo) + smoke UI de ids/campos

**Estado:** `HECHA`

---

### P5 — Importación mínima twin (CSV/Excel plantilla)

**Objetivo:** no depender solo del formulario twin a mano.

**Hacer:**
- Plantilla CSV (y/o xlsx si openpyxl gratis en local) documentada
- Endpoint o flujo UI: subir → validar → `PUT snapshot` (nueva ModelVersion)
- Informe de errores de validación (schema `CompanyTwinSnapshot`)
- Fixtures sintéticas en repo; datos reales fuera de git (R7)

**No hacer:** conectores Holded/Odoo/PSD2, mapeo contable completo asistido (eso puede ser P5.1 / fase posterior).

**Spec:** PRODUCTO §25 importación · MODELO snapshot · VALIDACION datos.

**DoD:**
- [x] Plantilla en repo + README de columnas
- [x] Import feliz → snapshot current nuevo
- [x] Import inválido → 400 con detalle; tests

**Estado:** `HECHA`

---

### P6 — Sensibilidad / “qué tendría que pasar”

**Objetivo:** no fingir análisis en la UI.

**Inventario (2026-10-04):** `analysis_plan` existía en `new_site` pero **no ejecutaba sweeps**. MOTOR M8: analytics solo cambia inputs y re-llama `calculate()`.

**Hacer:**
- Engine: `analytics/sensitivity.py` (direct ±10%, inversa binaria, stress §5.5)
- API: `POST /companies/{id}/packs/{pack_id}/sensitivity`
- UI: botón en informe; pinta solo respuesta API
- MVP pack: `new_site` (otros → 400 sin analysis_plan)

**No hacer:** Monte Carlo, correlaciones inventadas.

**DoD:**
- [x] Inventario documentado; sweeps reales vía `calculate()`
- [x] API + tests sin floats; MV current no muta
- [x] UI smoke sin cifras inventadas en JS

**Estado:** `HECHA`

---

### P7 — Usabilidad del camino crítico

**Objetivo:** que alguien no técnico complete twin → decisión → informe → seguimiento sin explicación de la API.

**Hacer (solo UI estática; mismos endpoints/números):**
- Stepper 4 pasos: Twin | Decisión | Informe | Seguimiento
- Lenguaje de gerente (jerga API solo en detalle/auditoría)
- Demo one-click: empresa + twin + `new_site` listos para calcular
- Informe: resumen humano arriba; tablas/trazabilidad/sensibilidad colapsables
- Errores accionables (sin dump JSON crudo)
- Hint corto por pack

**No hacer:** PDF, auth, Next.js, F9, packs nuevos, Monte Carlo, endpoints nuevos, V6.

**DoD:**
- [x] Stepper + copy + demo one-click en UI estática
- [x] Informe resumen-primero; errores accionables; sin `Math.` financiero en JS
- [x] Tests UI P7 + smokes previos verdes
- [x] Plan/docs satélite actualizados

**Estado:** `HECHA`

---

### P8 — Fácil de entender + UI de producto vendible

**Objetivo:** gerente/CFO poco técnico entiende y completa el flujo; la UI transmite producto B2B serio (“Atlantic Ledger”), no formulario genérico.

**Principios:**
1. Claridad: lenguaje de negocio, una CTA primaria por paso, jerga API solo en detalle.
2. Presencia visual: Fraunces + DM Sans; atmósfera gris-azul; acento teal `#0B6E6B`; métricas hero; sin purple/Inter/glow.

**Hacer (solo UI estática; mismos endpoints/números):**
- Sistema visual Atlantic Ledger
- Informe humano; comparación 3 escenarios visible; sensibilidad tabular
- Twin/import/seguimiento guiados; validación pre-run; loading/éxitos
- Imprimir informe (`@media print`) — sin PDF servidor

**No hacer:** auth, F9, Home, packs nuevos, Monte Carlo, PDF servidor, Next.js, conectores, V6 bloqueante.

**DoD:**
- [x] Principios + dirección visual en este plan
- [x] Look Atlantic Ledger; informe/compare/sensibilidad/print
- [x] CTA primaria; siguientes pasos; errores accionables; sin `Math.` financiero
- [x] Tests UI P8 + suite previa; docs satélite

**Estado:** `HECHA`

---

### P9 — Twin profesional + calidad de datos

**Objetivo (uso C):** twin creíble; sin twin bueno el resto miente.

**Hacer:**
- Editor twin: caja/políticas + CRUD mínimo ingresos/costes en UI (snapshot PUT existente)
- Panel calidad del twin (checklist factual, sin scores inventados)
- Import CSV con feedback humano de calidad

**No hacer:** auth, conectores ERP, F9.

**DoD:**
- [x] Editor streams en UI; calidad vía API/UI
- [x] Tests; docs

**Estado:** `HECHA`

---

### P10 — Informe entregable profesional

**Objetivo:** descargar informe defendible (no solo print del navegador).

**Hacer:**
- `POST` informe ejecutivo HTML descargable (contenido ⊆ run API)
- Botón UI «Descargar informe»
- Sin cifras inventadas en plantilla

**No hacer:** WeasyPrint obligatorio si falla en Windows; auth.

**DoD:**
- [x] Endpoint + UI download; tests smoke
- [x] `API.md` actualizado

**Estado:** `HECHA`

---

### P11 — Twin Loop de producto

**Objetivo:** seguimiento usable entre decisiones.

**Hacer:**
- Flujo guiado decisiones → actuals → sesgos
- Vista forecast vs actuals (solo datos API)
- Copy de recordatorio de revisión en UI

**DoD:**
- [x] UX seguimiento sin jerga; tests smoke

**Estado:** `HECHA`

---

### P12 — Liquidez como producto recurrente

**Objetivo:** uso frecuente entre CAPEX.

**Hacer:**
- Camino «Revisar liquidez» (pack `liquidity_plan`) con UX centrada en caja
- Resultado legible con métricas motor (`min_cash`, policies, shortfalls)
- Sin inventar `analysis_plan` si el pack no lo tiene

**DoD:**
- [x] Entrada liquidez + resultado claro; tests

**Estado:** `HECHA`

---

### P13 — Home mínima + navegación

**Objetivo:** producto navegable, no un studio suelto.

**Hacer:**
- Home: empresa, resumen twin, atajos Decidir / Liquidez / Seguimiento
- Selector empresas (`GET /companies`) sin login
- Nav global Atlantic Ledger

**DoD:**
- [x] Home + nav + list companies; docs cierre uso C

**Estado:** `HECHA`

---

### P14 — UX producto perfecto (sin V6)

**Objetivo:** gerente entiende y usa el producto en &lt;2 min sin tutor. Rediseño IA/UI (no más features de motor).

**Principios:** una pregunta por pantalla; una sola navegación; progressive disclosure; 3 jobs en Home; resultado = 1 métrica dominante + 1 CTA.

**Hacer:**
- Shell sidebar (Inicio / Decidir / Liquidez / Seguimiento / Datos); quitar nav+stepper duplicados
- Home 3 tarjetas; wizards Decidir/Liquidez; resultado hero
- Detalle técnico solo bajo demanda

**No hacer:** V6, auth, F9, Next.js, cambiar motor.

**DoD:**
- [x] Nav única; Home 3 jobs; wizards; resultado hero
- [x] Tests UI P14 + suite verde; docs

**Estado:** `HECHA`

---

### P15 — Flujo humano (intuición real)

**Objetivo:** primer minuto y camino crear→decidir→entender→registrar legibles sin tutor. Stack estático; sin React/Next.

**Hacer:**
- Onboarding: Crear empresa | Cargar demo; jobs gated; select honesto
- Demo narrada + banner; Resultado en sidebar; job cards CTA
- Formato números `es-ES`; métricas visibles; Twin Loop humano

**No hacer:** V6, auth, F9, Next.js, React Bits, cambiar motor/API.

**DoD:**
- [x] Home 2 caminos; crear visible; demo narrada; números legibles
- [x] Tests UI P15 + suite verde; docs

**Estado:** `HECHA`

---

### Auth local (diferida)

Login multi-usuario **no** es prioridad. Posible fase futura aparte.

**Estado:** `DIFERIDA`

---

### F9 — IA (referencia; no parte de este plan activo)

Sigue en `PLAN_IMPLEMENTACION.md`: orquestador + tools tipadas; **nunca calcula**.  
Requiere decisión explícita de coste (API LLM vs Ollama local).

**Estado:** `DIFERIDA`

---

## 5. Checklist producto usable (must de esta etapa)

| Must | Fase | Hecho |
|---|---|---|
| Run API 6 packs | P1 | [x] |
| UI 6 packs | P2 | [x] |
| Informe + variantes legible | P3 | [x] |
| History + actuals + calib. en UI | P4 | [x] |
| Import plantilla CSV | P5 | [x] |
| Sensibilidad new_site | P6 | [x] |
| Usabilidad camino crítico | P7 | [x] |
| Acabado profesional (claridad + UI) | P8 | [x] |
| Twin profesional + calidad | P9 | [x] |
| Informe descargable | P10 | [x] |
| Twin Loop producto | P11 | [x] |
| Liquidez primer nivel | P12 | [x] |
| Home + navegación | P13 | [x] |
| UX producto perfecto | P14 | [x] |
| Flujo humano | P15 | [x] |
| Auth local | — | diferida |
| IA chat | F9 | diferida |

---

## 6. Protocolo de sesión (igual espíritu que F0–F8)

1. Abrir **este plan** → fase activa  
2. Abrir specs citadas  
3. Listar archivos a tocar  
4. Tests DoD primero o junto  
5. Implementar hasta verde  
6. Marcar fase `HECHA` aquí + `DOCUMENTACION.md`  
7. ADR si decisión nueva  
8. Actualizar `API.md` / `ARQUITECTURA.md` solo con lo real  

**Prompt tipo:**

> Implementa solo la fase Px de `PLAN_PRODUCTO.md`.  
> Spec: […].  
> No implementes fuera de esa fase.  
> Si falta detalle, pregunta; no inventes.  
> DoD: [checklist].

---

## 7. Relación con el plan F0–F8

| Documento | Rol ahora |
|---|---|
| `PLAN_IMPLEMENTACION.md` | Histórico + reglas R1–R10; F9 diferida |
| **`PLAN_PRODUCTO.md`** | **Fase activa de desarrollo de producto** |
| `VALIDACION.md` / V6 | Paralelo (sesión humana); no bloquea P1–P14 |

---

## 8. Estado global

| Fase | Nombre | Estado |
|---|---|---|
| P1 | API 6 packs | HECHA |
| P2 | UI 6 packs | HECHA |
| P3 | Informe usable | HECHA |
| P4 | Twin Loop UI | HECHA |
| P5 | Import CSV | HECHA |
| P6 | Sensibilidad | HECHA |
| P7 | Usabilidad camino crítico | HECHA |
| P8 | Claridad + UI vendible | HECHA |
| P9 | Twin profesional + calidad | HECHA |
| P10 | Informe descargable | HECHA |
| P11 | Twin Loop producto | HECHA |
| P12 | Liquidez primer nivel | HECHA |
| P13 | Home + navegación | HECHA |
| P14 | UX producto perfecto | HECHA |
| P15 | Flujo humano | HECHA |
| Auth | Login local | DIFERIDA |
| F9 | IA | DIFERIDA |

**Fase activa actual:** ninguna Px must pendiente — **flujo humano P15 cerrado**; F9/auth/V6 diferidos

---

## 9. Changelog

| Versión | Fecha | Cambio |
|---|---|---|
| 2.3 | 2026-10-04 | P15 HECHA: flujo humano (onboarding, demo narrada, formato, loop) |
| 2.2 | 2026-10-04 | P14 HECHA: UX shell único, Home 3 jobs, wizards, resultado hero |
| 2.1 | 2026-10-04 | P9–P13 HECHAS: twin quality, informe HTML, loop, liquidez, home; uso C profesional (dev) |
| 2.0 | 2026-10-04 | Plan uso C: P9–P13 PENDIENTES (twin, informe, loop, liquidez, home); auth diferida |
| 1.10 | 2026-10-04 | P8 HECHA: Atlantic Ledger + claridad gerente (compare visible, sensibilidad tabular, print) |
| 1.9 | 2026-10-04 | P8 PENDIENTE: claridad gerente + UI Atlantic Ledger |
| 1.8 | 2026-10-04 | P7 HECHA: stepper, demo one-click, informe-primero, errores accionables |
| 1.7 | 2026-10-04 | P7 PENDIENTE: usabilidad camino crítico (stepper, demo, informe-primero) |
| 1.6 | 2026-10-04 | P6 HECHA: sensitivity engine+API+UI (new_site); P1–P6 cerradas |
| 1.5 | 2026-10-04 | P5 HECHA: import CSV twin + plantilla; P1–P5 cerradas |
| 1.4 | 2026-10-04 | P4 HECHA: Twin Loop UI + GET decisions; fase activa P5 |
| 1.3 | 2026-10-04 | P3 HECHA: informe ejecutivo + comparar 3 variantes; fase activa P4 |
| 1.2 | 2026-10-04 | P2 HECHA: Decision Studio 6 packs + smoke tests; fase activa P3 |
| 1.1 | 2026-10-04 | P1 HECHA: `POST /packs/{id}/run` + tests 6 packs; fase activa P2 |
| 1.0 | 2026-10-04 | Plan producto P1–P5 post F0–F8; F9 fuera; fase activa P1 |

---

*Norma: programar producto usable sin este plan abierto = riesgo de scope creep (Home, PDF, chat, conectores). La fase activa es la única licencia para escribir código.*
