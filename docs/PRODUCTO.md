# FINANCE TWIN — Documento Maestro de Producto

**Financial Decision Platform for SMEs**

| | |
|---|---|
| **Versión** | 1.0 |
| **Fecha** | Octubre 2026 |
| **Estado** | Definición de producto (pre-desarrollo) |
| **Autor** | Hugo |
| **Repositorio** | `Hugoesin19/FinanceTwin` (privado) |
| **Contexto** | Doble vía: producto B2B real + TFG (ADE + Informática) |

---

## 0. Cómo usar este documento

Este documento es la **fuente de verdad conceptual** del producto. Si algo no está aquí, no está decidido. Si algo contradice esto, se actualiza aquí primero.

Está dividido en cuatro bloques:

| Bloque | Secciones | Para qué sirve |
|---|---|---|
| **Estrategia** | 1–8 | Qué construimos, para quién y por qué |
| **Producto** | 9–20 | Qué hace exactamente el sistema |
| **Ingeniería** | 21–26 | Cómo se construye |
| **Ejecución** | 27–34 | Fases, validación, riesgos, siguiente paso |

**Regla de mantenimiento:** cada decisión importante se registra en la sección 34 (Registro de decisiones). Nada se decide "en una conversación" sin bajarlo aquí.

---

# BLOQUE I — ESTRATEGIA

## 1. Resumen ejecutivo

Finance Twin es una **plataforma de decisión financiera para pymes**. Construye un gemelo financiero de la empresa — un modelo estructurado y vivo de cómo funciona económicamente — y permite al gerente **simular decisiones importantes antes de ejecutarlas**, entender su impacto en liquidez, deuda y rentabilidad, y después **medir si las hipótesis eran buenas**.

La frase que resume el producto:

> **Antes de gastar 300.000 €, pruébalo aquí.**

### Las tres piezas que lo definen

**1. Un modelo vivo de la empresa.** No hojas sueltas: una representación conectada donde ventas, cobros, costes, pagos, deuda e inversión se relacionan. Cambias una variable y el sistema propaga las consecuencias.

**2. Un estudio de decisiones.** El gerente plantea una decisión real ("abrir una segunda tienda", "pedir un préstamo de 200.000 €", "comprar la furgoneta o leasing") y el sistema construye el escenario, calcula el impacto y genera un informe ejecutivo con VAN, TIR, payback, caja mínima y necesidad de financiación.

**3. Un bucle de aprendizaje.** Cada decisión se registra con sus hipótesis y su motivo. Meses después se compara con la realidad. Con el tiempo, el sistema sabe que *esta empresa* sobreestima ventas un 11 % y subestima CAPEX un 9 %, y lo aplica a las decisiones futuras.

### El principio arquitectónico no negociable

> **La IA interpreta. El motor calcula.**

Los números salen de un motor financiero determinista, reproducible y auditable. La IA hace que el sistema sea usable por alguien que no sabe finanzas: entiende la pregunta, pide los datos que faltan, explica el resultado y redacta el informe. **La IA nunca produce una cifra financiera.**

### Qué no es

- No es contabilidad. No sustituye a Holded, Sage, A3, Odoo ni a la gestoría.
- No es un ERP.
- No es un software de tesorería más (Agicap, Trezy, predicta).
- No es "ChatGPT conectado a tus números".

Finance Twin se coloca **por encima** de todo eso, consume su información, y resuelve una capa que hoy está vacía para la pyme: **decidir el dinero grande con método**.

---

## 2. El problema

### 2.1 Lo que pasa hoy en una pyme

Una pyme de 2–15 M€ de facturación toma entre 2 y 6 decisiones financieras **grandes** al año: abrir un local, comprar maquinaria, pedir financiación, contratar un equipo, ampliar almacén, entrar en un canal nuevo. Cada una compromete entre 50.000 € y 500.000 €.

Y se deciden así:

1. El gerente tiene una intuición.
2. Alguien hace un Excel. A veces el gerente, a veces la gestoría, a veces nadie.
3. El Excel tiene una columna de ventas optimista y una de costes incompleta.
4. Nadie modela el efecto sobre la **caja mes a mes**, solo sobre el beneficio anual.
5. Nadie calcula qué tendría que pasar para que la decisión fuera mala.
6. Se decide.
7. Nadie vuelve a abrir ese Excel para comparar con la realidad.

El resultado no es que las pymes decidan mal siempre. Es que **deciden sin instrumentos** y, sobre todo, **no acumulan ningún aprendizaje**. La misma empresa comete el mismo sesgo de previsión ocho veces sin saberlo.

### 2.2 Los cuatro fallos concretos

| Fallo | Consecuencia real |
|---|---|
| **Se mira el beneficio, no la caja** | Proyectos rentables que ahogan la tesorería en el mes 7 |
| **Una sola hipótesis** | Cero preparación para el escenario adverso |
| **No se modela la financiación** | Se descubre la necesidad de crédito cuando ya es urgente (y caro) |
| **No hay memoria** | El sesgo de previsión se repite indefinidamente |

### 2.3 Por qué el Excel no lo resuelve

El Excel sí puede hacer los cálculos. Lo que no puede hacer es:

- Mantenerse **actualizado** con la realidad de la empresa.
- Conectar la decisión con el **modelo completo** (si abres tienda, cambia la deuda, que cambia las cuotas, que cambian la caja).
- Guardar el **porqué** de la decisión.
- Comparar **previsión con realidad** sistemáticamente.
- Ser usable por alguien que no construye modelos financieros.

Y lo que sí hace, lo hace de forma **no auditable**: nadie sabe de dónde sale la celda `=H24*1,05`.

### 2.4 Por qué ahora

Tres cosas han cambiado:

1. **Los datos ya están digitalizados.** La pyme española factura en Holded/Sage/Odoo y tiene banca PSD2. Hace diez años esto era inviable.
2. **La IA abarata radicalmente la interfaz.** Lo que antes exigía que el usuario aprendiera un modelo financiero, hoy se resuelve conversando. La barrera de adopción era la UX, no el cálculo.
3. **El concepto está legitimado.** BCG y SAP publicaron el "Digital Financial Twin" para grandes corporaciones. Nadie lo ha bajado a la pyme.

---

## 3. Qué es Finance Twin

### 3.1 Definición

> Finance Twin es un **gemelo financiero** de la empresa: una representación estructurada, conectada y actualizada de su funcionamiento económico, sobre la que se pueden **simular decisiones, analizar su impacto, registrar su justificación y calibrar las hipótesis con la realidad**.

### 3.2 Por qué "Twin" y no "simulador"

Un simulador calcula escenarios. Un **twin** mantiene una correspondencia viva con el objeto real. La diferencia es el bucle:

```
empresa real
     ↓
  datos actuales
     ↓
  FINANCE TWIN  (modelo)
     ↓
  previsión
     ↓
  decisión  ──────────► se ejecuta en la empresa real
     ↓                              ↓
  registro de hipótesis      resultado real
     ↓                              ↓
     └──────────► comparación ◄─────┘
                      ↓
              desviación medida
                      ↓
              calibración del modelo
                      ↓
              mejor decisión siguiente
```

Sin ese bucle cerrado, el producto sería un simulador financiero bonito con churn alto. Con el bucle, cada mes que la empresa lo usa el producto se vuelve **más difícil de sustituir**, porque contiene el historial de decisiones de esa empresa.

### 3.3 La promesa en cinco verbos

El producto existe para que la pyme pueda:

1. **Entender** su situación económica real.
2. **Anticipar** su caja y sus riesgos.
3. **Probar** decisiones antes de ejecutarlas.
4. **Explicar** cada número con trazabilidad.
5. **Aprender** del sesgo de sus propias previsiones.

**Filtro de alcance:** si una funcionalidad propuesta no sirve directamente a uno de estos cinco verbos, no entra en el núcleo del producto.

---

## 4. Posicionamiento

### 4.1 Nombre y categoría

| Nivel | Denominación | Uso |
|---|---|---|
| **Marca** | Finance Twin | Nombre del producto |
| **Categoría comercial** | Financial Decision Platform for SMEs | Cómo se explica y se vende |
| **Concepto técnico** | Decision Finance Twin | Cómo se describe en arquitectura y TFG |

Frase puente:

> **Finance Twin** — *Financial Decision Platform for SMEs.*
> Construimos un gemelo financiero de tu empresa para que puedas simular decisiones antes de ejecutarlas.

### 4.2 Posicionamiento en una frase

> Finance Twin no compite por llevar la contabilidad de la pyme.
> Compite por ser **el sitio donde la pyme decide el dinero grande**.

### 4.3 Mapa de posicionamiento

```
                 DECISIÓN DE CAPITAL
                 (inversión, deuda, expansión)
                           ▲
                           │
   CapX AI            ┌────┴────┐
   Stratagio          │ FINANCE │        Armqu
   EasyPlanEx         │  TWIN   │        ValueWorks
   (cálculo aislado,  └────┬────┘        (twin real,
    sin twin)              │              pero mid-market
                           │              e implantación larga)
 PYME ◄────────────────────┼────────────────────► MID / ENTERPRISE
                           │
   Holded                  │              Pigment
   Agicap              Trezy             Anaplan
   predicta            Numio             Drivetrain
   Finamik                 │              Runway
                           ▼
                 OPERACIÓN CORRIENTE
                 (tesorería, reporting, cierre)
```

El cuadrante **pyme + decisión de capital** está estructuralmente vacío. Los que hacen cálculo de inversión no tienen modelo de empresa; los que tienen modelo de empresa no van a la pyme.

### 4.4 Diferenciación frente a cada vecino

| Competidor | Qué hace bien | Nuestro ángulo |
|---|---|---|
| **Holded / Agicap / Trezy / predicta** | Tesorería conectada, previsión 13 semanas, escenarios simples | No modelan decisiones de capital: ni VAN/TIR, ni estructura de financiación, ni memoria de decisiones |
| **Numio** | CFO virtual que interpreta contabilidad | Diagnóstico retrospectivo, no simulación prospectiva de decisiones |
| **CapX AI / Stratagio / EasyPlanEx / Business Case Calculator** | VAN, TIR, Monte Carlo, sensibilidad | Calculan el proyecto **aislado**, sin impacto sobre la caja y la deuda de la empresa real |
| **FounderConsole** | Twin + Monte Carlo + agentes + decision memory | Orientado a startups (runway, hiring, fundraising). No sirve a una pyme con tiendas, préstamos y activos |
| **Armqu** | Motor determinista + IA que explica + trazabilidad | Misma filosofía, pero mid-market industrial con implantación de 6–9 semanas. Nosotros: valor en menos de una hora |
| **Pigment / Anaplan / Runway / Drivetrain** | FP&A potente | Precio e implantación imposibles para la pyme |
| **BCG / SAP Digital Financial Twin** | Legitimación del concepto | Es narrativa para grandes cuentas, no producto |

### 4.5 El moat (qué nos hace difíciles de copiar)

Ordenado de más débil a más fuerte:

1. **Modelo de dominio pyme bien hecho** (replicable, pero costoso).
2. **Motor determinista + trazabilidad total** (replicable, pero es trabajo serio).
3. **Decision Packs por tipo de decisión** (replicable, se copia la UX).
4. **Decision History de la empresa** (no replicable: son *sus* decisiones).
5. **Calibración de sesgos por similitud histórica** (no replicable y mejora con el uso).
6. **Benchmarks anónimos entre pymes del mismo sector** (efecto red; solo accesible con base instalada).

El moat real son los puntos 4–6. Todo lo anterior es condición de entrada.

---

## 5. Estado del arte y competencia (resumen de investigación)

Investigación realizada en octubre de 2026. Conclusión: **no existe un clon exacto**, pero **todas las piezas existen por separado**. Esto es relevante para la memoria del TFG y para no hacer afirmaciones falsas.

### 5.1 Lo que sí existe

**Concepto "gemelo financiero" (enterprise)**
- BCG + SAP, *Why Your Company Needs a Digital Financial Twin* (2022). Define el concepto para grandes corporaciones.
- Capgemini Digital Twin for Finance.
- Norlean NOA (España): gemelo digital de organización con escenarios de cash flow.
- SIMCEL: twin de planificación integrada (demanda + supply + finanzas).

**Twin + Monte Carlo + agentes (startups)**
- FounderConsole: digital twin, Monte Carlo P10/P50/P90, agentes, decision engine. **La referencia más cercana a nuestra visión**, pero para startups.
- ValueWorks: data twin + agentes + Monte Carlo, mid-market.

**Motor determinista + IA explicativa**
- Armqu: *"Armqu does not use the AI to generate figures... The AI explains those results. It does not invent numbers."* Nuestra misma tesis arquitectónica, en manufactura mid-market.

**Tesorería y escenarios para pyme**
- España: Holded, Agicap, Trezy, predicta.es, Finamik, Numio.
- Internacional: Float, Cash Flow Frog, Obol, CFO Engine, LivePlan, Fathom.

**FP&A startup / mid-market**
- Runway, Mosaic, Cube, Pigment, Drivetrain, Vena, Planful, Datarails. Causal fue adquirida por LucaNet (2024).

**Valoración de inversiones aislada**
- CapX AI, Capex Stratagio, EasyPlanEx, Business Case Calculator, SimpleFeasibility.

**Academia**
- Digital twins aplicados a cash e inventario en cadena de suministro (varios papers 2022–2025).
- "Scenario memory" / "DecisionEpisode" para soporte de decisión en pymes: línea emergente, aún a nivel prototipo.
- Monte Carlo digital twin worldview (Purdue, WSC).

### 5.2 El hueco real

Nadie cubre simultáneamente:

```
modelo vivo de la pyme
+ decisión de capital (VAN/TIR/payback)
+ estructura de financiación
+ impacto en caja mes a mes
+ sensibilidad inversa
+ plan vs real
+ memoria de decisiones con calibración de sesgos
+ trazabilidad auditable
+ pyme tradicional (no startup SaaS)
+ datos imperfectos (Excel, Holded, banco)
```

### 5.3 Cómo formular esto en el TFG

❌ **No decir:** "no existe un gemelo financiero para empresas".
✅ **Decir:** "el mercado fragmenta tesorería operativa, FP&A y valoración de inversiones; no existe una plataforma que integre modelo de empresa, decisión de capital y calibración plan-real para la pyme tradicional".

---

## 6. Cliente objetivo

### 6.1 ICP v1 (deliberadamente estrecho)

| Dimensión | Definición |
|---|---|
| **Tamaño** | 0,5 – 15 M€ de facturación |
| **Empleados** | 5 – 100 |
| **Decisión** | El gerente/dueño decide; no hay comité de inversión |
| **Datos** | Contabilidad digitalizada (Holded, Sage, A3, Odoo, ContaPlus) o Excel usable |
| **Frecuencia de decisión** | 2–6 decisiones de capital al año |
| **Sectores de arranque** | Retail multi-establecimiento · hostelería en expansión · servicios con activos · industria ligera · distribución |
| **Geografía** | España primero (idioma, PSD2, plan contable, canal de asesorías) |

### 6.2 Fuera del ICP inicial

| Perfil | Por qué no |
|---|---|
| Startup SaaS con inversores | Runway y FounderConsole ya lo cubren; métricas distintas (ARR, burn, runway) |
| Autónomo / micro | No toma decisiones de capital relevantes; no paga |
| Grupo multi-país | Consolidación, divisas, intercompany: complejidad enorme para v1 |
| Gran empresa | Tiene FP&A y CFO; compra Pigment/Anaplan |

### 6.3 Personas

**Elena — Gerente / Dueña (comprador y usuario principal)**
- 45–60 años, no financiera de formación.
- Decide por intuición + consejo del asesor.
- Dolor: *"no sé si me puedo permitir esto"*.
- Quiere: una respuesta clara y un informe que pueda llevar al banco.
- No quiere: aprender a construir modelos financieros.
- **Interfaz: conversación + Decision Packs + informe.**

**Marcos — Controller / Responsable financiero (usuario avanzado, puede existir o no)**
- Lleva el Excel de la empresa.
- Dolor: mantener el modelo actualizado y defender sus números.
- Quiere: tocar hipótesis, ver fórmulas, exportar.
- Riesgo: puede verlo como amenaza → hay que posicionarlo como **su** herramienta.
- **Interfaz: dashboards + editor de hipótesis + motor visible.**

**Pilar — Asesora / Gestoría externa (canal clave en España)**
- Lleva 40–200 pymes.
- Dolor: le piden consejo estratégico y solo tiene datos contables retrospectivos.
- Quiere: vender un servicio de mayor valor sin multiplicar horas.
- **Interfaz: workspace multi-empresa + plantillas + informes con su marca.**

**Javier — Banco / Socio / Inversor (consumidor del output, no usuario)**
- Recibe el informe.
- Quiere: supuestos explícitos, escenario adverso, capacidad de repago.
- **Interfaz: PDF estructurado y auditable.**

### 6.4 Quién paga

El comprador es la **gerencia** (presupuesto de dirección, no de software contable). El canal más eficiente en España es la **asesoría**, que introduce el producto en su cartera. Esto define dos movimientos de producto: *self-serve ligero* para la pyme y *workspace* para el asesor.

---

## 7. Jobs to be done y casos de uso

### 7.1 El job principal

> *"Tengo que tomar una decisión que compromete una cantidad importante de dinero, y quiero saber qué le pasa a mi empresa si la tomo — antes de tomarla."*

### 7.2 Jobs secundarios

1. *"Quiero saber si voy a tener problemas de caja en los próximos meses."*
2. *"Necesito un informe creíble para pedir financiación."*
3. *"Quiero saber si lo que decidí el año pasado salió como esperaba."*
4. *"Quiero saber qué tendría que pasar para que esto saliera mal."*
5. *"Quiero comparar dos alternativas con el mismo criterio."*

### 7.3 Catálogo de decisiones (el corazón del producto)

Estas son las decisiones que el producto debe saber simular. Cada una se implementa como un **Decision Pack** (sección 13).

| # | Decisión | Prioridad | Variables clave |
|---|---|---|---|
| 1 | Abrir nuevo establecimiento / sede | **MVP** | CAPEX, alquiler, ventas rampa, personal, margen, fecha |
| 2 | Solicitar financiación | **MVP** | Importe, plazo, tipo, carencia, garantías, destino |
| 3 | Comprar activo (maquinaria, vehículo, local) | **MVP** | Precio, vida útil, financiación vs leasing vs contado, ahorro/ingreso asociado |
| 4 | Contratar personal | **MVP** | Coste total empresa, fecha, productividad esperada |
| 5 | Inversión genérica con retorno | **MVP** | CAPEX, flujos esperados, horizonte, tasa de descuento |
| 6 | Plan de liquidez / estrés de caja | **MVP** | Horizonte, hipótesis de cobro/pago, caja mínima |
| 7 | Cambio de precios / margen | Fase 1 | Elasticidad estimada, volumen, mix |
| 8 | Comprar vs alquilar vs leasing | Fase 1 | Comparativa de alternativas |
| 9 | Refinanciación / reestructuración de deuda | Fase 1 | Deuda actual, nueva estructura, coste |
| 10 | Ampliación de almacén / capacidad | Fase 1 | CAPEX, capacidad adicional, demanda |
| 11 | Entrada en canal / mercado nuevo | Fase 2 | Inversión comercial, rampa, coste de adquisición |
| 12 | Reducción de costes / cierre de línea | Fase 2 | Ahorro, coste de salida, impacto en ingresos |
| 13 | Compra de empresa / fondo de comercio | Fase 3 | Valoración, financiación, sinergias |
| 14 | Reparto de dividendos | Fase 3 | Caja disponible, política, fiscalidad |

### 7.4 El caso de uso canónico (el que hay que clavar)

Es el que se usa en demos, en el TFG y en la validación.

**Entrada del usuario (lenguaje natural):**

> "Quiero abrir una segunda tienda en Alicante en septiembre de 2027. Costaría unos 350.000 € y creo que vendería 40.000 € al mes."

**Lo que hace el sistema:**

1. Identifica el tipo de decisión → Decision Pack "Nuevo establecimiento".
2. Detecta qué información falta y pregunta **solo lo necesario** (margen esperado, alquiler, personal, rampa de ventas, forma de financiación).
3. Propone valores por defecto a partir del modelo actual de la empresa (margen histórico, coste medio de personal, plazos de cobro reales).
4. Construye el escenario sobre el modelo existente, sin alterar el escenario base.
5. Calcula estructura de financiación y su servicio de deuda.
6. Proyecta P&L y cash flow mes a mes durante el horizonte.
7. Calcula VAN, TIR, payback y caja mínima proyectada.
8. Ejecuta variantes: base, conservador, adverso.
9. Comprueba las políticas de la empresa (caja mínima, techo de deuda, payback máximo).
10. Ejecuta sensibilidad inversa: ¿a partir de qué nivel deja de funcionar?
11. Consulta el Decision History: ¿hay decisiones similares? ¿qué sesgo tuvieron?
12. Genera informe ejecutivo con trazabilidad completa.

**Salida (resumen ejecutivo):**

```
IMPACTO ESPERADO — Escenario base
  Inversión total                 350.000 €
  VAN (8 %, 7 años)              +185.000 €
  TIR                                 14,3 %
  Payback                           4,2 años
  Caja mínima proyectada           73.000 €  (mes 14)
  Necesidad adicional de financiación  120.000 €

CUMPLIMIENTO DE POLÍTICAS
  ✓ Caja mínima (50.000 €)        cumple (73.000 €)
  ✓ Payback máximo (5 años)       cumple (4,2)
  ⚠ Deuda / EBITDA (máx. 3,0x)    3,2x en meses 9–18

RIESGOS DETECTADOS
  · El proyecto depende de alcanzar ~34.000 €/mes de ventas.
  · Con ventas un 15 % inferiores al escenario base, la caja
    mínima cae a 12.000 €, por debajo de la política de empresa.

¿QUÉ TENDRÍA QUE PASAR PARA QUE NO FUNCIONE?
  El VAN pasa a ser negativo si:
   · las ventas bajan de 31.500 €/mes, o
   · el margen cae por debajo del 27 %, o
   · el CAPEX supera los 425.000 €.

MEMORIA DE DECISIONES
  He encontrado 3 decisiones similares en tu historial:
   · Previsión de ventas: de media un 18 % superior a la realidad.
   · CAPEX real: de media un 9 % superior al presupuestado.
   · Punto de equilibrio: 4,2 meses más tarde de lo previsto.
  → ¿Quieres generar un escenario corregido con tus sesgos históricos?
```

Ese último bloque es el que ningún competidor tiene para pyme. Es la pieza que convierte el producto en algo que mejora con el uso.

---

## 8. Principios de producto

Reglas de diseño. Sirven para resolver discusiones futuras sin volver a abrir el debate.

### P1 — La IA interpreta, el motor calcula
Ninguna cifra financiera se genera por un modelo de lenguaje. La IA traduce intención a parámetros, explica resultados y redacta. El motor es determinista y reproducible.

### P2 — Todo número es trazable
Cada cifra mostrada debe poder responder: qué fórmula, qué datos, qué supuestos, qué escenario, qué versión, quién y cuándo. Sin excepciones.

### P3 — El escenario base es sagrado
Los escenarios nunca sobreescriben el modelo base. Se crean al lado, se comparan, y solo se promueven explícitamente.

### P4 — Valor antes de integración
El sistema debe dar valor con un Excel y una hora de trabajo. Las integraciones aceleran, no habilitan. Nunca "implántanos ocho semanas y luego verás".

### P5 — Profundidad por vertical, no amplitud por módulo
Mejor modelar excelentemente retail multi-tienda que mediocremente catorce sectores.

### P6 — El porqué vale tanto como el número
Una decisión sin su justificación registrada es un dato incompleto. El motivo es campo de primera clase, no una nota.

### P7 — El sistema no decide
Marca cumplimiento de políticas, cuantifica riesgos y propone alternativas. La decisión y la responsabilidad son del humano. Esto es diseño, no cobardía: es lo que lo hace aceptable en un entorno financiero.

### P8 — Honestidad sobre la incertidumbre
Si falta un dato, se dice. Si una proyección es frágil, se marca. Nunca se rellena un hueco con una cifra plausible inventada.

### P9 — Determinismo y reproducibilidad
El mismo escenario con las mismas entradas da exactamente el mismo resultado, hoy y en dos años. Las simulaciones estocásticas llevan semilla registrada.

### P10 — Lenguaje de empresario, no de analista
"Necesitas 120.000 € más de financiación en marzo" en lugar de "working capital gap de 120 k€ en M+5".

---

# BLOQUE II — PRODUCTO

## 9. Arquitectura funcional

Seis capas. Cada una con una responsabilidad única.

```
┌─────────────────────────────────────────────────────────────────┐
│  G · INTERFACES                                                 │
│  Chat guiado · Decision Packs · Dashboards · Informes · API     │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  F · CAPA DE IA (orquestador + agentes)                         │
│  Interpretar · preguntar · proponer · explicar · redactar       │
│  NUNCA calcula                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  E · DECISION LAYER                                             │
│  Decision Studio · Decision History · Calibración de sesgos     │
│  Risk Radar · Guardrails de política                            │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  D · ANALYTICS ENGINE                                           │
│  Escenarios · Sensibilidad · Sensibilidad inversa               │
│  Stress test · Monte Carlo (fase posterior)                     │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  C · MOTOR FINANCIERO DETERMINISTA                              │
│  P&L · Cash flow · Balance simplificado · Deuda · Amortización  │
│  VAN · TIR · Payback · Ratios                                   │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  B · MODELO DE LA EMPRESA (Company Twin)                        │
│  Entidades conectadas · hipótesis · políticas · versiones       │
└─────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────┐
│  A · CAPA DE DATOS                                              │
│  Excel/CSV · Holded/Sage/Odoo · Banco PSD2 · Entrada manual     │
│  Normalización · mapeo · calidad de datos                       │
└─────────────────────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────┐
        │  H · TRUST LAYER (atraviesa todo)        │
        │  Audit trail · versiones · linaje        │
        │  permisos · explicabilidad               │
        └──────────────────────────────────────────┘
```

### Responsabilidades y límites

| Capa | Responsabilidad | Prohibido |
|---|---|---|
| A · Datos | Ingerir, normalizar, mapear, medir calidad | Calcular resultados |
| B · Modelo | Representar la empresa y sus hipótesis | Lógica de cálculo financiero |
| C · Motor | Calcular estados financieros y métricas | Decidir, interpretar, recomendar |
| D · Analytics | Variar hipótesis y explorar el espacio | Reimplementar fórmulas del motor |
| E · Decisión | Gestionar decisiones, historial, políticas, riesgos | Calcular |
| F · IA | Traducir, preguntar, explicar, redactar | Producir cifras |
| G · Interfaz | Presentar y capturar | Lógica de negocio |
| H · Trust | Registrar y explicar el origen de todo | — |

---

## 10. El modelo de la empresa (Company Twin)

### 10.1 Decisión de alcance: grafo reducido primero

El "Enterprise Financial Graph" completo es el destino, no el punto de partida. El MVP implementa **tres bloques conectados**:

```
                         EMPRESA
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
     OPERACIÓN           FINANZAS         FINANCIACIÓN
         │                  │                  │
      ventas           P&L / Balance        préstamos
      costes           cash flow            intereses
      cobros           ratios               cuotas
      pagos            caja                 carencias
         │                  │                  │
         └──────────────────┼──────────────────┘
                            ▼
                      FINANCE TWIN
                            ▼
                     DECISION ENGINE
                            ▼
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
     escenarios       sensibilidad        stress test
```

**Se añade después** (en este orden): activos y amortización → empleados detallados → inventario y aprovisionamiento → fiscalidad detallada → clientes/proveedores individualizados.

Motivo: con estos tres bloques ya se pueden simular **las seis decisiones del MVP**. Añadir inventario y RRHH detallados antes de tener el bucle cerrado multiplica la fragilidad sin añadir decisiones nuevas.

### 10.2 Entidades del modelo

#### Company
Datos identificativos, sector, ejercicio fiscal, moneda, configuración contable.

#### RevenueStream (línea de ingreso)
```
id, nombre, tipo (recurrente | transaccional | proyecto)
unidad_negocio (p.ej. tienda, canal, línea)
volumen_base, precio_medio, estacionalidad[12]
crecimiento (% anual o curva)
margen_bruto_%
dias_cobro_medio
fecha_inicio, fecha_fin (opcional)
```

#### CostItem (coste)
```
id, nombre
naturaleza (fijo | variable | semivariable)
base (importe | % de ingreso | por unidad)
importe o porcentaje
unidad_negocio (opcional)
dias_pago_medio
estacionalidad, crecimiento
fecha_inicio, fecha_fin
```

#### Payroll (coste de personal — simplificado en MVP)
```
id, puesto, nº_personas
coste_total_empresa_mensual   (salario + SS + variables)
fecha_incorporacion, fecha_salida
unidad_negocio
```

#### Loan (préstamo)
```
id, nombre, entidad
principal, tipo_interes (fijo | variable + referencia)
plazo_meses, sistema_amortizacion (francés | lineal | bullet)
carencia_meses (de capital | total)
comisiones_apertura, otros_costes
fecha_disposicion
garantías (texto), covenants (opcional)
```

#### Asset (activo)
```
id, nombre, tipo
coste_adquisicion, fecha_adquisicion
vida_util_meses, metodo_amortizacion (lineal | acelerada)
valor_residual
forma_adquisicion (contado | préstamo | leasing | renting)
```

#### Investment (inversión / proyecto)
```
id, nombre, tipo_decisión
capex_total, desglose_capex[]
fecha_inicio, horizonte_meses
flujos_incrementales (derivados de RevenueStreams y CostItems asociados)
financiación_asociada (Loan[] | recursos propios)
tasa_descuento
```

#### BusinessUnit (unidad de negocio)
Permite separar "tienda Valencia" de "tienda Alicante" y consolidar. Esencial para la decisión canónica.

#### WorkingCapitalPolicy
```
dias_cobro_clientes, dias_pago_proveedores
dias_inventario (si aplica)
iva_periodicidad, otros_impuestos
```

#### CompanyPolicy (guardrails)
```
caja_minima
deuda_ebitda_maximo
payback_maximo_meses
tir_minima
cobertura_servicio_deuda_minima (DSCR)
porcentaje_maximo_capex_sobre_caja
```

#### Assumption (hipótesis)
```
id, nombre, valor, unidad
origen (histórico | usuario | sectorial | calibrado)
confianza (alta | media | baja)
rango_plausible (min, max)
justificación
```

Las hipótesis son **entidades de primera clase**, no celdas. Esto es lo que permite trazabilidad, sensibilidad automática y calibración.

### 10.3 Grafo de propagación

Lo que hace que esto sea un modelo y no una hoja:

```
RevenueStream ──► ingresos ──► margen bruto ──► EBITDA
      │                                            │
      └──► cobros (días cobro) ──┐                 │
                                 ├──► CASH FLOW ◄──┤
CostItem ──► costes ─────────────┤                 │
      └──► pagos (días pago) ────┤                 │
                                 │                 │
Payroll ──► coste personal ──────┤                 │
                                 │                 │
Loan ──► intereses ──────────────┼──► resultado ◄──┘
   └──► amortización capital ────┤       financiero
                                 │
Asset ──► amortización contable ─┼──► resultado
   └──► desembolso CAPEX ────────┤
                                 │
Impuestos ◄── base imponible ────┤
                                 ▼
                            CAJA FINAL
                                 │
                   ┌─────────────┼─────────────┐
                   ▼             ▼             ▼
            caja mínima    necesidad      ratios y
                           financiación   políticas
```

### 10.4 Versionado del modelo

Cada cambio relevante genera una versión. Esto permite:
- Reconstruir qué sabía el sistema cuando se tomó una decisión (crítico para Decision History).
- Auditar.
- Comparar modelo de hace seis meses con el actual.

```
ModelVersion: id, company_id, created_at, created_by,
              parent_version, changelog, snapshot (datos completos)
```

---

## 11. Motor financiero determinista

El componente más crítico del sistema. Si esto falla, nada más importa.

### 11.1 Requisitos

| Requisito | Significado |
|---|---|
| **Determinista** | Mismas entradas → mismas salidas, siempre |
| **Reproducible** | Un cálculo de 2027 se puede repetir idéntico en 2030 |
| **Explicable** | Cada salida puede desglosarse hasta sus entradas |
| **Versionado** | El motor tiene versión; los resultados guardan con qué versión se calcularon |
| **Testeable** | Batería de casos con resultados conocidos |
| **Granularidad mensual** | El mes es la unidad mínima (la caja se rompe en meses, no en años) |

### 11.2 Salidas

**Cuenta de resultados (P&L) mensual**
```
Ingresos
− Coste de ventas
= Margen bruto
− Gastos de personal
− Otros gastos de explotación
= EBITDA
− Amortizaciones
= EBIT
− Gastos financieros
= BAI
− Impuesto sobre beneficios
= Resultado neto
```

**Cash flow mensual (método directo)**
```
Cobros de clientes
− Pagos a proveedores
− Pagos de personal
− Otros pagos de explotación
− Pagos de impuestos (IVA, IS)
= Flujo de explotación
− CAPEX
+ Desinversiones
= Flujo de inversión
+ Disposición de préstamos
− Amortización de capital
− Intereses
+/− Aportaciones / dividendos
= Flujo de financiación
= FLUJO NETO DEL PERÍODO
+ Caja inicial
= CAJA FINAL
```

**Balance simplificado**
Activo no corriente (neto de amortización), clientes, inventario (si aplica), tesorería, patrimonio neto, deuda a largo y corto, proveedores, administraciones públicas.

**Métricas de inversión**
```
VAN  = Σ [ FCt / (1+r)^t ] − I₀
TIR  = r tal que VAN = 0            (bisección / Newton-Raphson)
Payback simple y descontado
ROI, ROCE
```

**Ratios**
Liquidez (corriente, ácida), endeudamiento (deuda/EBITDA, deuda/patrimonio), cobertura (DSCR, EBITDA/intereses), rotación (clientes, proveedores, existencias), rentabilidad (ROE, ROA, margen).

**Necesidades de financiación**
Déficit máximo acumulado, mes de caja mínima, importe y fecha de necesidad adicional.

### 11.3 Orden de cálculo

Importa, porque hay dependencias circulares que hay que resolver explícitamente:

```
1. Ingresos por línea y unidad de negocio
2. Costes variables (dependen de ingresos)
3. Costes fijos y personal
4. EBITDA
5. Amortizaciones (desde Assets)
6. Servicio de deuda (desde Loans)       ← cuadros de amortización
7. Resultado antes de impuestos
8. Impuestos
9. Devengos → flujos de caja (aplicar días de cobro/pago)
10. Flujo de caja y saldo acumulado
11. Detección de déficit → ¿necesidad de financiación?
12. [Opcional] Si hay déficit y la política lo permite:
    financiación automática → volver a 6 (máx. N iteraciones)
13. Balance
14. Ratios y métricas
15. Comprobación de políticas (guardrails)
```

El paso 12 es la única circularidad y se resuelve iterativamente con tope de iteraciones y convergencia declarada. Debe ser **opcional y explícito**: el usuario decide si el sistema "tapa" déficits con deuda automática o los muestra crudos.

### 11.4 Cuadro de amortización de préstamos

Sistema francés (cuota constante):

```
cuota = P · i / (1 − (1+i)^−n)

donde P = principal pendiente, i = tipo periódico, n = períodos restantes
```

Con carencia de capital: durante la carencia solo se pagan intereses (`P · i`) y la cuota se recalcula al terminar. Con carencia total: los intereses se capitalizan.

El motor debe generar el cuadro completo mes a mes y exponerlo como parte de la trazabilidad.

### 11.5 Tratamiento del IVA y los impuestos

En MVP, simplificado pero explícito:
- IVA: tipo medio configurable, liquidación trimestral o mensual, con desfase real de pago.
- Impuesto de sociedades: tipo configurable, pago fraccionado aproximado.
- Se documenta como **simplificación conocida**, no se oculta.

Esto es importante: el IVA es una de las principales causas de tensión de caja en pymes y un modelo que lo ignore pierde credibilidad inmediata.

### 11.6 Diseño técnico del motor

**Implementación recomendada:** Python puro (sin dependencias de hoja de cálculo), con:
- Tipos de datos monetarios en `Decimal` (nunca `float` para dinero).
- Estructura de cálculo como **grafo de dependencias** (DAG) evaluado en orden topológico.
- Cada nodo registra: entradas, fórmula, salida.
- Salida de cálculo acompañada de **traza** (sección 18).

```python
# Boceto conceptual
@dataclass(frozen=True)
class CalculationResult:
    pnl: MonthlyStatement
    cash_flow: MonthlyStatement
    balance: MonthlyStatement
    metrics: InvestmentMetrics
    ratios: RatioSet
    policy_checks: list[PolicyCheck]
    trace: CalculationTrace       # linaje completo
    engine_version: str
    model_version: str
    computed_at: datetime
```

**Prohibido:** que la capa de IA o la interfaz recalculen nada. Un único motor, una única verdad.

### 11.7 Validación del motor

Cuatro niveles (detalle en sección 25):
1. Casos unitarios con resultado conocido a mano.
2. Comparación contra Excel de referencia construido independientemente.
3. Reconstrucción de los estados financieros históricos reales de una empresa.
4. Invariantes contables: balance cuadra, suma de flujos = variación de caja, etc.

---

## 12. Analytics Engine

Explora el espacio alrededor del escenario base. **Nunca reimplementa fórmulas**: siempre llama al motor.

### 12.1 Escenarios

```
Scenario:
  id, nombre, tipo (base | optimista | conservador | adverso | custom)
  parent_scenario
  overrides: [ { assumption_id, valor_nuevo, justificación } ]
  bloqueado (sí/no)
  created_by, created_at
```

Características:
- Se construyen por **diferencias** sobre el base, no por copia completa. Así, si cambia el base, los escenarios se actualizan.
- Comparación lado a lado de N escenarios.
- Bloqueo de escenarios aprobados (equivalente a "presupuesto cerrado").

### 12.2 Análisis de sensibilidad (directo)

Para cada hipótesis marcada como sensible, variar ±X % y medir impacto en las métricas objetivo (VAN, caja mínima, TIR).

Salida: **tornado chart** ordenado por impacto. Responde a *"¿de qué depende realmente esta decisión?"*.

### 12.3 Sensibilidad inversa — *"¿Qué tendría que pasar?"*

La función más diferencial del producto y, probablemente, la más útil para un gerente.

En lugar de "¿es rentable?", responde: **"¿qué tendría que ocurrir para que dejara de ser rentable?"**

**Mecánica:** para cada variable, buscar el valor umbral que hace que una métrica objetivo cruce un límite. Es un problema de búsqueda de raíz:

```
encontrar x tal que  métrica(x) = umbral

método: bisección sobre el rango plausible de la hipótesis,
        llamando al motor en cada iteración
```

**Salidas típicas:**
```
El VAN pasa a ser negativo si:
  · ventas < 31.500 €/mes        (−21 % sobre hipótesis)
  · margen < 27 %                (−5 p.p.)
  · CAPEX > 425.000 €            (+21 %)

La caja mínima baja de 50.000 € si:
  · ventas < 36.200 €/mes        (−9,5 %)   ← restricción más próxima
```

Lo importante no es el número, es señalar **cuál es la restricción más cercana**. En el ejemplo, la liquidez es el límite real, no la rentabilidad.

### 12.4 Stress test

Escenarios adversos predefinidos, combinables:
- Caída de ventas (−10 %, −20 %, −30 %).
- Alargamiento de plazos de cobro (+15, +30 días).
- Subida de tipos de interés (+100, +200, +300 pb).
- Subida de costes de aprovisionamiento.
- Pérdida del cliente principal.
- Retraso en la apertura / puesta en marcha.

Salida: tabla de resultados y señalización de qué políticas se incumplen en cada caso.

### 12.5 Monte Carlo (fase posterior, no MVP)

Cuando entre:
- Distribuciones por hipótesis: triangular (min/moda/max) como opción por defecto para un gerente, normal/lognormal para usuarios avanzados.
- Correlaciones entre variables (al menos ventas-costes variables).
- 1.000–10.000 iteraciones, **semilla registrada** para reproducibilidad.
- Salidas: distribución de VAN, P10/P50/P90, probabilidad de VAN > 0, probabilidad de incumplir caja mínima.

**Regla de comunicación:** nunca presentar como "tienes un 78 % de probabilidad de éxito". Presentar como: *"bajo las hipótesis y rangos introducidos, el proyecto mantiene VAN positivo en el 78 % de los escenarios simulados"*. La diferencia no es cosmética: es honestidad sobre el modelo.

**Prioridad:** la sensibilidad inversa vende más a una pyme que 10.000 simulaciones. Monte Carlo es sofisticación, no valor nuclear.

### 12.6 Goal seek

*"¿Cuántas ventas necesito para que el payback sea de 3 años?"* Misma mecánica que la sensibilidad inversa, con objetivo en lugar de umbral.

---

## 13. Decision Studio

El corazón funcional. Donde el usuario pasa de "tengo una duda" a "tengo una decisión documentada".

### 13.1 Decision Packs

Un Decision Pack es una **plantilla de decisión**: inputs mínimos, lógica de construcción de escenario, outputs fijos e informe estándar.

Existen porque el chat libre atrae pero no convierte. El gerente no sabe qué preguntar; sabe qué quiere hacer.

**Anatomía de un Pack:**
```
DecisionPack:
  id, nombre, tipo
  descripción para el usuario
  inputs_requeridos: [ campo, tipo, ayuda, valor_por_defecto_derivado ]
  inputs_opcionales: [...]
  entidades_que_crea: [ RevenueStream, CostItem, Asset, Loan, ... ]
  métricas_objetivo: [ VAN, TIR, payback, caja_mínima, ... ]
  sensibilidades_automáticas: [ hipótesis clave ]
  stress_tests_por_defecto: [...]
  políticas_a_comprobar: [...]
  plantilla_informe: ref
  preguntas_de_calidad: [ "¿has considerado X?" ]
```

**Ejemplo — Pack "Nuevo establecimiento":**

| Input | Tipo | Valor por defecto propuesto |
|---|---|---|
| Ubicación / nombre | texto | — |
| Fecha de apertura | fecha | — |
| CAPEX total | € | — |
| Desglose CAPEX | obra, mobiliario, equipos, existencias iniciales, licencias | reparto típico del sector |
| Ventas en régimen | €/mes | media de establecimientos existentes |
| Rampa de ventas | % mes 1..12 | curva histórica de aperturas anteriores |
| Margen bruto | % | margen histórico de la empresa |
| Alquiler | €/mes | — |
| Personal | nº + coste | coste medio por empleado de la empresa |
| Otros costes operativos | €/mes o % ventas | ratio histórico |
| Financiación | % deuda / % recursos propios | — |
| Condiciones del préstamo | importe, plazo, tipo, carencia | — |
| Horizonte de análisis | años | 7 |
| Tasa de descuento | % | coste medio de la deuda + prima |

Los "valores por defecto propuestos" son lo que hace el producto **mágico frente al Excel**: el sistema ya conoce la empresa y no pregunta lo que puede deducir.

### 13.2 Flujo de una decisión

```
1. INICIO
   El usuario describe la decisión (chat) o elige un Pack.

2. CLASIFICACIÓN
   La IA identifica el Pack adecuado y lo confirma con el usuario.

3. RECOPILACIÓN
   Se piden solo los datos que faltan. Se proponen valores derivados
   del modelo. Cada valor queda marcado con su origen y confianza.

4. CONSULTA AL HISTORIAL
   ¿Hay decisiones similares? Se muestran sus sesgos.
   Se ofrece crear además un "escenario corregido".

5. CONSTRUCCIÓN
   Se crean las entidades del escenario sobre el modelo (sin tocar el base).

6. CÁLCULO
   El motor calcula base + variantes (conservador, adverso).

7. ANÁLISIS
   Sensibilidad, sensibilidad inversa, stress tests, políticas.

8. PRESENTACIÓN
   Resumen ejecutivo + detalle + trazabilidad + riesgos.

9. DELIBERACIÓN
   El usuario ajusta hipótesis, compara alternativas, pide variantes.

10. REGISTRO DE DECISIÓN
    Aprobada / rechazada / aplazada
    + motivo + responsable + alternativas descartadas
    + riesgos aceptados explícitamente

11. SEGUIMIENTO
    Se programan hitos de revisión (3, 6, 12 meses).
```

El paso 10 es el que casi todos los competidores se saltan y el que habilita todo el valor a largo plazo.

### 13.3 Comparador de alternativas

Mismo problema, varias soluciones, mismo criterio:

| | Comprar al contado | Préstamo 5 años | Leasing 4 años | Renting |
|---|---|---|---|---|
| Desembolso inicial | 80.000 € | 20.000 € | 8.000 € | 0 € |
| Coste total | 80.000 € | 91.400 € | 88.200 € | 94.800 € |
| Impacto caja mínima | −80.000 € | −6.200 € | −5.400 € | −4.900 € |
| VAN diferencial | base | −4.100 € | −2.800 € | −6.300 € |
| Deuda/EBITDA | 2,1x | 2,8x | 2,6x | 2,1x |
| Política cumplida | ⚠ caja | ✓ | ✓ | ✓ |

### 13.4 Informe ejecutivo

Estructura fija, exportable a PDF:

1. **Decisión planteada** — qué se evalúa, en una frase.
2. **Recomendación del sistema** — no "hazlo", sino: cumple/no cumple políticas, principales riesgos, condiciones de viabilidad.
3. **Resultado económico** — VAN, TIR, payback, caja mínima, necesidad de financiación.
4. **Proyección** — P&L y cash flow mensual (gráfico + tabla).
5. **Escenarios** — base / conservador / adverso.
6. **Qué tendría que pasar** — umbrales críticos.
7. **Riesgos y restricción más próxima.**
8. **Hipótesis utilizadas** — con origen y nivel de confianza de cada una.
9. **Anexo de trazabilidad** — datos, fórmulas, versiones.

**Variante "Banco / Socio"** (sección 15.3).

---

## 14. Decision History y calibración de sesgos

Esta sección describe el **activo diferencial** del producto. Trátese como pieza de primer nivel, no como registro accesorio.

### 14.1 Qué se registra

Una decisión no es un escenario. Es un escenario **más el contexto humano**.

```
Decision:
  id, número (#024), company_id
  título                      "Abrir tienda Alicante"
  tipo (DecisionPack)
  fecha_decisión
  estado (aprobada | rechazada | aplazada | ejecutada | cancelada)

  # Lo cuantitativo
  escenario_id                (congelado, inmutable)
  model_version               (qué sabía el sistema entonces)
  engine_version
  hipótesis[]                 valor + origen + confianza
  métricas_previstas          VAN, TIR, payback, caja mín., financiación
  proyección_congelada        P&L y cash flow mes a mes previstos

  # Lo cualitativo — igual de importante
  motivo                      por qué se decide esto
  responsable                 quién decide
  alternativas_descartadas[]  qué se consideró y por qué no
  riesgos_aceptados[]         qué se asumió consciente
  condiciones                 "si en 6 meses no llegamos a X, revisamos"
  políticas_incumplidas[]     y justificación de la excepción

  # Seguimiento
  hitos_revisión[]            fechas programadas
  resultados_reales[]         (se van rellenando)
  desviaciones[]              (calculadas)
  cierre                      valoración final cuando concluye
```

### 14.2 Ejemplo

```
DECISIÓN #024 — Abrir tienda Alicante
Fecha: 14/02/2027            Estado: ejecutada
Responsable: CEO

HIPÓTESIS
  Ventas en régimen      40.000 €/mes    (origen: usuario, confianza media)
  Margen bruto           31 %            (origen: histórico, confianza alta)
  CAPEX                  350.000 €       (origen: presupuesto proveedor)
  Alquiler               3.500 €/mes     (origen: contrato)
  Rampa                  12 meses        (origen: apertura Valencia 2024)

DECISIÓN         Aprobada
FINANCIACIÓN     200.000 € préstamo (7 años, 4,5 %) + 150.000 € recursos propios
MOTIVO           Saturación de la tienda de Valencia; demanda detectada en
                 Alicante por ventas online; oportunidad de local en zona prime.
ALTERNATIVAS     · Ampliar Valencia → descartada: sin espacio disponible
DESCARTADAS      · Franquicia → descartada: pérdida de control de marca
RIESGOS          · Dependencia de alcanzar 34.000 €/mes
ACEPTADOS        · Deuda/EBITDA sube a 3,2x durante 9 meses (política: máx. 3,0x)
CONDICIÓN        Si a los 6 meses las ventas < 30.000 €/mes, revisar plantilla.
REVISIONES       3 meses · 6 meses · 12 meses

──────────────────────────────────────────────────────────────

RESULTADO A 6 MESES (14/08/2027)

                        Previsto      Real      Desviación
  Ventas /mes           40.000 €    34.800 €      −13,0 %
  Margen bruto            31,0 %      29,2 %      −1,8 p.p.
  CAPEX                350.000 €   372.000 €       +6,3 %
  Mes de break-even      mes 9      mes 13       +4 meses
  Caja mínima           73.000 €    41.000 €      −43,8 %

  ⚠ La caja mínima real quedó por debajo de la política (50.000 €).
```

### 14.3 Cálculo de sesgos

Con varias decisiones acumuladas, el sistema calcula desviaciones sistemáticas:

```
BiasProfile (por empresa, por tipo de decisión, por variable):
  variable                "ventas_en_régimen"
  n_observaciones         6
  sesgo_medio             +18 %      (previsión por encima de realidad)
  sesgo_mediano           +15 %
  desviación_típica        9 p.p.
  dirección               sobreestimación sistemática
  confianza               media  (n < 10)
  último_actualizado      2027-08-14
```

**Cómo se calcula el sesgo de una variable:**
```
desviación_i = (previsto_i − real_i) / previsto_i
sesgo        = mediana(desviación_i)      ← mediana, no media: robusta a outliers
```

**Umbrales de comunicación:**
| n | Qué se puede decir |
|---|---|
| 1–2 | Solo mostrar casos individuales. Nada de "tiendes a". |
| 3–5 | "En las últimas N decisiones similares, la desviación fue de X%." |
| 6–9 | "Parece haber una tendencia a sobreestimar..." (confianza media) |
| ≥10 | "Sistemáticamente sobreestimas las ventas iniciales un X%." |

Esto es importante por **rigor y por credibilidad**: afirmar un sesgo con dos datos destruye la confianza del usuario financiero.

### 14.4 Calibración por similitud — la función estrella

Cuando el usuario inicia una decisión nueva, el sistema busca decisiones **similares** en el historial.

**Criterios de similitud:**
- Mismo tipo (DecisionPack).
- Magnitud comparable (CAPEX en el mismo orden).
- Misma unidad de negocio o sector de actividad.
- Antigüedad (ponderar más las recientes).

**Lo que presenta:**
```
Antes de construir el escenario, he encontrado 6 decisiones similares
en vuestro historial.

  Previsión de ventas       de media un 18 % superior a la realidad
  Desviación de CAPEX       de media un 9 % superior a lo presupuestado
  Tiempo a break-even       de media 4,2 meses más tarde de lo previsto
  Margen realizado          de media 1,5 p.p. por debajo del previsto

  ¿Quieres que genere también un ESCENARIO CALIBRADO aplicando
  vuestras desviaciones históricas?

  [ Sí, añade el escenario calibrado ]   [ No, solo mis hipótesis ]
```

Si acepta, se genera un escenario adicional con hipótesis corregidas y se compara:

| | Mis hipótesis | Calibrado con historial |
|---|---|---|
| Ventas | 40.000 € | 32.800 € |
| CAPEX | 350.000 € | 381.500 € |
| VAN | +185.000 € | +31.000 € |
| Payback | 4,2 años | 6,1 años |
| Caja mínima | 73.000 € | 38.000 € ⚠ |

Esta tabla es, probablemente, **la pantalla más valiosa de todo el producto**. Convierte una intuición optimista en una conversación informada, usando los datos de la propia empresa y sin que ninguna IA haya inventado nada.

### 14.5 Qué NO es esto

No es "la IA aprende mágicamente". Es **backtesting y calibración estadística** de hipótesis, con una metodología explicable y auditable. Esa honestidad es un activo, tanto comercial como académico.

### 14.6 Evolución: benchmarks sectoriales

Cuando haya base instalada, con datos anonimizados y agregados:
- "Las pymes de retail de tu tamaño sobreestiman las ventas de nuevas aperturas un 22 % de media."
- Útil para empresas sin historial propio (resuelve el arranque en frío).
- Requiere consentimiento explícito, anonimización real y masa crítica. No antes.

---

## 15. Capacidades complementarias

### 15.1 Risk Radar (detección proactiva)

El sistema no espera a que le pregunten. Analiza el modelo y señala situaciones que requieren atención.

**Reglas iniciales (deterministas, con umbrales configurables):**

| Señal | Regla | Mensaje |
|---|---|---|
| **Liquidez** | Caja proyectada cae por debajo de la política en los próximos N meses | "La previsión de caja muestra una reducción significativa en los próximos 6 meses" |
| **Endeudamiento** | Deuda/EBITDA proyectado supera el límite | "El calendario de inversiones podría elevar el ratio por encima del límite configurado" |
| **Capital inmovilizado** | Crecimiento de existencias > crecimiento de ventas | "El inventario está consumiendo más caja que el crecimiento de ventas" |
| **Concentración de vencimientos** | > X % de la deuda vence en una ventana de N meses | "Existe una concentración de vencimientos en el periodo X" |
| **Plazos de cobro** | Días de cobro reales se deterioran vs histórico | "El plazo medio de cobro ha aumentado N días" |
| **Dependencia** | Un cliente/línea supera X % de los ingresos | "Concentración de ingresos en un cliente" |
| **Desviación de plan** | Real se desvía > X % del plan vigente | "Las ventas acumuladas están un X % por debajo del plan" |

Y entonces ofrece: **"¿Quieres que simule alternativas?"** → entra en Decision Studio.

**Importante:** reglas y umbrales primero; detección por ML mucho después. Una regla explicable vale más que un modelo opaco en un contexto financiero.

### 15.2 Guardrails de política

La empresa configura sus límites una vez:

```
Caja mínima operativa            50.000 €
Deuda / EBITDA máximo                3,0x
DSCR mínimo                          1,3x
Payback máximo                     5 años
TIR mínima exigida                    12 %
CAPEX máximo / caja disponible        60 %
```

Y el sistema, en cada escenario, **marca cumplimiento**:

```
✓ Caja mínima        cumple (73.000 € vs 50.000 €)
✓ Payback            cumple (4,2 vs 5 años)
✓ TIR                cumple (14,3 % vs 12 %)
⚠ Deuda / EBITDA     INCUMPLE en meses 9–18 (máx. 3,2x vs límite 3,0x)
```

Esto cambia el tono del producto: de oráculo que recomienda a **sistema de control que informa**. Es lo que lo hace aceptable para un financiero y defendible ante un tribunal.

Si se aprueba una decisión incumpliendo una política, se exige justificación y queda registrada. Eso es gobernanza real.

### 15.3 Modo Banco / Socio

Informe orientado a obtener financiación o convencer a un socio. Momento de compra urgente y ROI evidente.

Contenido:
- Situación financiera actual con ratios estándar.
- Proyecto y su encaje estratégico.
- Necesidad de financiación: importe, destino, calendario.
- Capacidad de repago: DSCR proyectado mes a mes.
- Escenario adverso y qué pasa con el servicio de deuda en él.
- Garantías y estructura propuesta.
- Supuestos explícitos y trazabilidad.

Esta pieza puede ser, en la práctica, **el principal gancho comercial**: la pyme no compra "planificación financiera", compra "que el banco me diga sí".

### 15.4 Advisor Workspace

Para asesorías y gestorías (canal B2B2B en España).

- Vista multi-empresa con alertas agregadas.
- Plantillas de modelo por sector reutilizables.
- Informes con la marca de la asesoría (white-label ligero).
- Permisos por cliente y por usuario.
- Posible modelo de cobro por cartera.

### 15.5 Assumption Library

Repositorio de hipótesis de la empresa con su historia:
- Valor actual, valores históricos, origen, confianza.
- Qué decisiones usaron cada hipótesis.
- Qué desviación tuvo cada una.

Permite responder: *"¿de dónde viene el 31 % de margen que usamos siempre?"*.

---

## 16. Capa de IA

### 16.1 Lo que la IA sí hace

| Función | Descripción |
|---|---|
| **Interpretar** | Lenguaje natural → tipo de decisión + parámetros estructurados |
| **Detectar huecos** | Qué falta para poder calcular; preguntar solo eso |
| **Proponer valores** | Sugerir valores por defecto a partir del modelo e histórico |
| **Explicar** | Traducir el resultado del motor a lenguaje de empresario |
| **Redactar** | Generar informes a partir de resultados estructurados |
| **Mapear datos** | Ayudar a mapear cuentas contables y columnas de Excel al modelo |
| **Buscar similitud** | Encontrar decisiones comparables en el historial |
| **Resumir y señalar** | Priorizar lo relevante de un conjunto de resultados |

### 16.2 Lo que la IA nunca hace

- No calcula cifras financieras.
- No estima un VAN, una TIR, una cuota ni un flujo.
- No inventa un dato que falta (lo pide o lo marca como desconocido).
- No aprueba ni rechaza decisiones.
- No modifica el modelo base sin confirmación explícita del usuario.

### 16.3 Arquitectura de agentes

**MVP: un orquestador + herramientas (tools) sobre el motor.** Varios agentes sin un motor robusto es teatro arquitectónico.

**Fase posterior: agentes especializados**, todos sobre el mismo modelo central:

| Agente | Función |
|---|---|
| **Scenario Agent** | Traduce intención en escenario estructurado |
| **Financial Analyst** | Interpreta estados financieros y ratios |
| **Treasury Agent** | Analiza liquidez y cash flow |
| **Investment Agent** | Interpreta métricas de inversión |
| **Financing Agent** | Analiza estructura y alternativas de financiación |
| **Risk Agent** | Busca vulnerabilidades y restricciones próximas |
| **Reporting Agent** | Redacta informes para dirección, banco o socios |
| **Data Agent** | Mapeo e ingesta, detección de problemas de calidad |

**Regla de oro:** los agentes **no son la fuente de verdad**. El motor lo es.

```
Agentes:  interpretan → consultan → proponen → explican
Motor:    calcula
```

### 16.4 Herramientas expuestas a la IA

La IA opera exclusivamente mediante llamadas a funciones tipadas. No tiene acceso libre a la base de datos ni genera SQL arbitrario.

```
get_company_model(company_id, version?)
get_historical_financials(company_id, period)
propose_defaults(decision_type, company_id)
create_scenario(company_id, base_scenario, overrides[])
run_calculation(scenario_id)                      → CalculationResult
run_sensitivity(scenario_id, assumptions[], range)
run_inverse_sensitivity(scenario_id, metric, threshold)
run_stress_test(scenario_id, stress_profile)
check_policies(scenario_id)
find_similar_decisions(company_id, decision_type, magnitude)
get_bias_profile(company_id, decision_type, variable)
apply_bias_calibration(scenario_id, bias_profile)
compare_scenarios(scenario_ids[])
get_plan_vs_actual(company_id, period)
generate_report(scenario_id, template)
```

### 16.5 Control de alucinación

| Mecanismo | Cómo |
|---|---|
| **Separación estricta** | La IA no puede emitir cifras; las plantillas de salida se rellenan con valores del motor |
| **Citación obligatoria** | Toda cifra en texto generado referencia un identificador de resultado del motor |
| **Validación de salida** | Post-proceso que comprueba que las cifras del texto coinciden con las del motor; si no, se rechaza |
| **Explicitar lo desconocido** | Si falta un dato, el agente lo pide; no estima |
| **Confirmación de intención** | Antes de construir un escenario, se muestra al usuario la interpretación estructurada |
| **Trazabilidad del prompt** | Se registra qué contexto y qué herramientas se usaron |

### 16.6 Interfaz conversacional: alcance correcto

El chat es **puerta de entrada y capa explicativa**, no el producto. El valor sigue estando en el escenario estructurado y el informe auditable. Diseño: chat para plantear y entender; Packs y dashboards para trabajar; informe para decidir y comunicar.

---

## 17. Twin Loop (plan vs real)

Lo que justifica el nombre y lo que genera retención.

### 17.1 El ciclo

```
1. El modelo refleja la situación actual (datos reales).
2. Se construye una previsión y se congela como plan.
3. Se toma una decisión y se registra con sus hipótesis.
4. Pasa el tiempo. Entran datos reales.
5. El sistema compara plan vs real, mes a mes.
6. Calcula desviaciones y las atribuye a causas.
7. Actualiza el BiasProfile de la empresa.
8. El modelo se recalibra.
9. La siguiente decisión parte de mejor información.
```

### 17.2 Congelación de planes

Cada plan aprobado se congela de forma inmutable: valores, versión del modelo, versión del motor, fecha, autor. Sin esto, la comparación plan-real es manipulable y pierde todo valor (es el error clásico del Excel: se "actualiza" el plan y nadie recuerda qué se prometió).

### 17.3 Análisis de desviaciones

```
Desviación de EBITDA del trimestre:  −42.000 €

Descomposición:
  Efecto volumen de ventas      −31.000 €   (ventas 13 % por debajo)
  Efecto margen                  −8.500 €   (margen 1,8 p.p. menor)
  Efecto costes de personal      +4.200 €   (contratación retrasada)
  Efecto otros costes            −6.700 €   (suministros por encima)
```

La descomposición es cálculo determinista, no interpretación de la IA. La IA solo lo narra.

### 17.4 Cadencia

- **Mensual:** actualización de datos reales, comparación, alertas.
- **Hitos de decisión:** revisión a 3, 6, 12 meses de cada decisión registrada.
- **Anual:** recalibración completa de hipótesis y revisión de políticas.

---

## 18. Trust Layer: trazabilidad y auditoría

Sin esta capa no hay producto financiero B2B vendible. Es requisito, no adorno.

### 18.1 Anatomía de un número trazable

Cualquier cifra del sistema puede desplegarse así:

```
RESULTADO
  VAN = 185.230 €

CÓMO SE HA CALCULADO
  VAN = Σ [ FCt / (1+r)^t ] − I₀
  Flujo año 1    52.000 €
  Flujo año 2    61.000 €
  Flujo año 3    68.000 €
  ...
  Tasa de descuento    8,0 %
  Inversión inicial    350.000 €

DATOS UTILIZADOS
  Ventas históricas 2023–2026      (origen: Holded, importado 02/10/2026)
  Margen bruto medio               (calculado: 31,2 %)
  Coste medio de personal          (calculado desde nóminas)
  Parámetros introducidos          (usuario: CEO, 14/02/2027)

SUPUESTOS
  Crecimiento de ventas      5 % anual     (origen: usuario, confianza media)
  Inflación de costes        3 % anual     (origen: sectorial)
  Margen bruto              32 %           (origen: histórico, confianza alta)
  Rampa de ventas           12 meses       (origen: apertura anterior)

ESCENARIO
  Base  ·  variantes disponibles: conservador, adverso, calibrado

METADATOS
  Versión del modelo     v47
  Versión del motor      2.3.1
  Calculado              14/02/2027 18:42
  Por                    CEO (hugo@empresa.es)
  Semilla aleatoria      n/a (cálculo determinista)
```

### 18.2 Audit trail

Registro inmutable de:
- Cambios en el modelo (qué, quién, cuándo, valor anterior y nuevo).
- Creación y modificación de escenarios.
- Ejecuciones de cálculo (con versión de motor).
- Decisiones registradas y sus cambios de estado.
- Incumplimientos de política aprobados y su justificación.
- Importaciones de datos y su resultado.
- Accesos y exportaciones.

### 18.3 Linaje de datos

Cada dato del modelo sabe de dónde viene:
```
origen: importado | calculado | introducido | calibrado | sectorial
fuente: Holded / fichero.xlsx / usuario X / BiasProfile
fecha_obtención
confianza: alta | media | baja
```

### 18.4 Calidad de datos visible

El sistema muestra abiertamente el estado de su información:
```
CALIDAD DEL MODELO

  ✓ Ventas              36 meses de histórico
  ✓ Costes              36 meses de histórico
  ⚠ Plazos de cobro     estimados (no hay detalle de facturas)
  ⚠ Inventario          no modelado
  ✗ Personal            solo coste agregado, sin desglose

  Fiabilidad para proyección de caja:  MEDIA
  Principal limitación: los plazos de cobro son una media estimada.
```

Esto es aplicación directa del principio P8. Un sistema que dice lo que no sabe genera más confianza que uno que lo oculta.

---

## 19. Interfaces y experiencia de usuario

### 19.1 Tres niveles de usuario, tres interfaces

| Usuario | Interfaz principal | Qué ve |
|---|---|---|
| **CEO / Gerente** | Conversación + Decision Packs + informe | Preguntas, decisiones, resultados en lenguaje claro |
| **Controller / Asesor** | Dashboards + editor de hipótesis | Modelo, escenarios, fórmulas, comparativas |
| **Analista** | Tablas, trazabilidad, exportación | Datos, linaje, detalle mes a mes |

Mismo modelo, misma verdad, tres profundidades.

### 19.2 Mapa de pantallas

```
HOME / SITUACIÓN
  · Caja actual y proyectada (12 meses)
  · Semáforo de políticas
  · Risk Radar: señales abiertas
  · Decisiones en seguimiento
  · Calidad del modelo

DECISION STUDIO
  · Nueva decisión (chat o Packs)
  · Escenarios en curso
  · Comparador de alternativas
  · Resultados y análisis
  · Generación de informe

MODELO (la empresa)
  · Líneas de ingreso
  · Costes
  · Personal
  · Deuda
  · Activos
  · Unidades de negocio
  · Hipótesis (Assumption Library)
  · Políticas

PROYECCIONES
  · P&L mensual
  · Cash flow mensual
  · Balance
  · Ratios
  · Plan vs real

DECISION HISTORY
  · Historial de decisiones
  · Detalle de cada decisión
  · Desviaciones
  · Perfil de sesgos de la empresa

DATOS
  · Fuentes conectadas
  · Importaciones
  · Mapeo de cuentas
  · Calidad

INFORMES
  · Ejecutivo
  · Banco / socio
  · Seguimiento mensual
  · Exportaciones

CONFIGURACIÓN
  · Empresa, usuarios, permisos
  · Políticas y umbrales
  · Audit trail
```

### 19.3 Experiencia de la primera sesión (crítica)

Objetivo: **primer escenario útil en menos de 30 minutos**, sin integraciones.

```
1. Crear empresa (2 min)
   Nombre, sector, ejercicio.

2. Cargar datos (10 min)
   Opción A: plantilla Excel de Finance Twin
   Opción B: exportación de contabilidad (Holded, A3, Sage) + mapeo asistido
   Opción C: entrada manual guiada (ventas, costes, deuda, caja)

3. Revisar el modelo propuesto (5 min)
   El sistema muestra lo que ha entendido y pide confirmación
   de lo que tiene baja confianza.

4. Configurar políticas (3 min)
   Caja mínima, techo de deuda. Valores por defecto sectoriales.

5. Primera decisión (10 min)
   Elegir un Pack y simular.

6. Ver el informe.
```

El punto 3 es donde se gana o se pierde la confianza. Nunca presentar un modelo como "listo" si tiene huecos: presentarlo con su calidad declarada.

### 19.4 Principios de UX

- **Progresivo:** empezar simple, profundizar si se pide.
- **Nunca una celda huérfana:** todo dato tiene etiqueta, unidad y origen visible.
- **Comparación por defecto:** los números solos no informan; siempre frente a plan, histórico o política.
- **Lenguaje de negocio:** "necesitas 120.000 € más en marzo", no "WC gap M+5".
- **Alertas accionables:** cada señal lleva un "¿quieres simular alternativas?".
- **Nada irreversible sin confirmación:** especialmente promover un escenario a base.

---

## 20. Datos e integraciones

### 20.1 Estrategia por etapas

| Etapa | Fuente | Fricción | Cuándo |
|---|---|---|---|
| **1** | Plantilla Excel/CSV de Finance Twin | Mínima | MVP |
| **2** | Exportación de contabilidad (Holded, A3, Sage, ContaPlus) + mapeo asistido | Baja | MVP |
| **3** | API de Holded / Odoo + banco PSD2 vía agregador | Media | Fase 2 |
| **4** | ERP completo, facturación, nóminas | Alta | Fase 3 |

Aplicación del principio P4: **valor sin integración**. El Excel no es el plan B, es el plan A de la primera hora.

### 20.2 Normalización

Lo que entra es un caos de planes contables, nombres y formatos. Lo que se guarda es un modelo canónico:

```
Fichero / API
     ↓
Detección de formato y estructura
     ↓
Mapeo de cuentas → categorías canónicas    (asistido por IA, confirmado por usuario)
     ↓
Validación (cuadres, huecos, outliers)
     ↓
Informe de calidad al usuario
     ↓
Carga en el modelo con linaje registrado
```

### 20.3 Mapeo de cuentas

El Plan General Contable español da una base, pero cada empresa lo usa a su manera. El sistema:
- Propone mapeo por número de cuenta y descripción.
- Aprende del mapeo confirmado por el usuario (y lo reutiliza).
- Permite guardar plantillas de mapeo por asesoría (muy valioso para el canal).
- Nunca mapea en silencio algo con baja confianza.

### 20.4 Validaciones de calidad

- Cuadres contables básicos.
- Meses ausentes en el histórico.
- Valores atípicos (señalados, no eliminados).
- Coherencia entre devengo y cobro.
- Signos invertidos.
- Duplicados.

El resultado se presenta al usuario como **informe de calidad**, nunca se corrige silenciosamente.

---

# BLOQUE III — INGENIERÍA

## 21. Arquitectura técnica

### 21.1 Stack propuesto

| Capa | Tecnología | Por qué |
|---|---|---|
| **Motor financiero** | Python + `Decimal` | Precisión monetaria, legibilidad de fórmulas, testeable, ecosistema numérico |
| **API** | FastAPI (Python) | Mismo lenguaje que el motor, tipado con Pydantic, OpenAPI automático |
| **Base de datos** | PostgreSQL | Transaccional, JSONB para snapshots, maduro |
| **Frontend** | Next.js + TypeScript + React | Dashboards, buena DX, rendering de informes |
| **Gráficos** | Recharts o similar | Series temporales, tornado charts, waterfalls |
| **Cálculo asíncrono** | Cola de trabajos (Celery / RQ) | Monte Carlo y análisis masivos sin bloquear |
| **IA** | API de LLM con function calling | Herramientas tipadas, sin acceso directo a datos |
| **PDF** | Generación desde plantillas HTML | Informes consistentes y versionables |
| **Infra** | Contenedores + hosting europeo | RGPD, simplicidad operativa |

**Decisión clave:** el motor es una **librería Python independiente**, sin dependencias de web ni de base de datos. Se puede testear, versionar y auditar por separado. Esto también lo hace reutilizable y defendible en el TFG como artefacto propio.

### 21.2 Estructura del repositorio

```
FinanceTwin/
├── docs/
│   ├── PRODUCTO.md              ← este documento
│   ├── ARQUITECTURA.md
│   ├── MOTOR_FINANCIERO.md      ← especificación de fórmulas
│   ├── MODELO_DATOS.md
│   ├── DECISION_PACKS.md
│   ├── VALIDACION.md            ← protocolo de validación (TFG)
│   └── adr/                     ← registro de decisiones de arquitectura
├── engine/                      ← librería del motor (Python, independiente)
│   ├── financetwin_engine/
│   │   ├── model/               entidades del dominio
│   │   ├── calc/                P&L, cash flow, balance, deuda, métricas
│   │   ├── analytics/           escenarios, sensibilidad, stress, MC
│   │   ├── policies/            guardrails
│   │   ├── trace/               trazabilidad
│   │   └── version.py
│   └── tests/
│       ├── unit/
│       ├── golden/              casos con resultado conocido
│       └── invariants/          propiedades que siempre deben cumplirse
├── api/                         ← FastAPI
│   ├── routers/
│   ├── services/
│   ├── ai/                      orquestador y herramientas
│   └── tests/
├── web/                         ← Next.js
├── data/
│   ├── templates/               plantillas Excel de importación
│   ├── mappings/                plantillas de mapeo contable
│   └── sector_defaults/         valores por defecto sectoriales
└── scripts/
```

### 21.3 Esquema de datos (núcleo)

```sql
-- Organización
company(id, name, sector, fiscal_year_start, currency, created_at)
user(id, email, name, role)
company_user(company_id, user_id, role, permissions)

-- Modelo
model_version(id, company_id, parent_id, created_at, created_by,
              changelog, snapshot jsonb)

revenue_stream(id, company_id, model_version_id, name, type,
               business_unit_id, volume, price, margin_pct,
               seasonality jsonb, growth, collection_days,
               start_date, end_date)

cost_item(id, company_id, model_version_id, name, nature, basis,
          amount, pct_of_revenue, business_unit_id,
          payment_days, seasonality jsonb, growth,
          start_date, end_date)

payroll(id, company_id, model_version_id, role_name, headcount,
        monthly_total_cost, business_unit_id, start_date, end_date)

loan(id, company_id, model_version_id, name, lender, principal,
     interest_rate, rate_type, term_months, amortization_system,
     grace_months, grace_type, fees, disbursement_date)

asset(id, company_id, model_version_id, name, type, cost,
      acquisition_date, useful_life_months, depreciation_method,
      residual_value, acquisition_form)

business_unit(id, company_id, name, type, start_date)

assumption(id, company_id, model_version_id, name, value, unit,
           origin, confidence, min_plausible, max_plausible,
           justification)

company_policy(id, company_id, min_cash, max_debt_ebitda,
               min_dscr, max_payback_months, min_irr,
               max_capex_pct_cash)

-- Escenarios y cálculo
scenario(id, company_id, name, type, parent_scenario_id,
         base_model_version_id, overrides jsonb, locked,
         created_by, created_at)

calculation_run(id, scenario_id, engine_version, model_version_id,
                inputs_hash, results jsonb, trace jsonb,
                random_seed, computed_at, computed_by)

-- Decisiones
decision(id, company_id, number, title, decision_pack,
         decision_date, status,
         scenario_id, model_version_id, engine_version,
         forecast_metrics jsonb, frozen_projection jsonb,
         rationale, owner, discarded_alternatives jsonb,
         accepted_risks jsonb, conditions,
         policy_exceptions jsonb)

decision_milestone(id, decision_id, due_date, status, notes)

actual_result(id, decision_id, period, variable, forecast_value,
              actual_value, deviation_pct, source, recorded_at)

bias_profile(id, company_id, decision_pack, variable,
             n_observations, median_bias, mean_bias, std_dev,
             direction, confidence, updated_at)

-- Datos y confianza
data_source(id, company_id, type, name, config jsonb,
            last_sync, status)
import_run(id, data_source_id, started_at, finished_at,
           rows_processed, quality_report jsonb, status)
account_mapping(id, company_id, source_account, source_description,
                target_category, confidence, confirmed_by)

-- Trust
audit_log(id, company_id, user_id, entity_type, entity_id,
          action, old_value jsonb, new_value jsonb, timestamp)
```

### 21.4 API (superficie principal)

```
# Empresa y modelo
GET    /companies/{id}
GET    /companies/{id}/model
POST   /companies/{id}/model/versions
GET    /companies/{id}/model/quality

# Datos
POST   /companies/{id}/imports
GET    /companies/{id}/imports/{import_id}
POST   /companies/{id}/mappings

# Escenarios
POST   /companies/{id}/scenarios
GET    /scenarios/{id}
POST   /scenarios/{id}/calculate
POST   /scenarios/{id}/lock
GET    /scenarios/compare?ids=

# Análisis
POST   /scenarios/{id}/sensitivity
POST   /scenarios/{id}/inverse-sensitivity
POST   /scenarios/{id}/stress-test
POST   /scenarios/{id}/monte-carlo
POST   /scenarios/{id}/goal-seek
GET    /scenarios/{id}/policy-check

# Decisiones
POST   /companies/{id}/decisions
GET    /companies/{id}/decisions
GET    /decisions/{id}
POST   /decisions/{id}/actuals
GET    /companies/{id}/bias-profile
POST   /scenarios/{id}/apply-calibration

# Riesgos
GET    /companies/{id}/risk-radar

# Plan vs real
GET    /companies/{id}/plan-vs-actual?period=

# Informes
POST   /scenarios/{id}/reports
GET    /reports/{id}

# IA
POST   /companies/{id}/assistant/messages
```

### 21.5 Decisiones de arquitectura clave

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| Motor como librería independiente | Lógica dentro de la API | Testeabilidad, auditabilidad, reutilización, defensa en TFG |
| `Decimal` para dinero | `float` | Errores de redondeo inaceptables en finanzas |
| Escenarios por diferencias | Copia completa del modelo | Los escenarios se actualizan si cambia el base |
| Snapshots inmutables de planes | Plan editable | Sin congelación, plan vs real es manipulable |
| IA con herramientas tipadas | IA con acceso a datos / SQL | Control de alucinación y de seguridad |
| Granularidad mensual | Anual o trimestral | La caja se rompe en meses |
| PostgreSQL + JSONB | Base documental pura | Necesitamos transaccionalidad y flexibilidad en snapshots |

---

## 22. Seguridad, privacidad y cumplimiento

Esto es información financiera de empresas. El estándar es alto desde el diseño, aunque las certificaciones vengan después.

### 22.1 Seguridad

- Cifrado en tránsito (TLS) y en reposo.
- Aislamiento estricto por empresa (multi-tenant con verificación en cada consulta).
- Permisos por rol: propietario, financiero, consulta, asesor externo.
- Autenticación con segundo factor para roles con acceso a datos financieros.
- Conexiones a contabilidad y banco en **solo lectura**.
- Secretos y credenciales fuera del repositorio; rotación.
- Registro de accesos y exportaciones.

### 22.2 Privacidad y RGPD

- Hosting en la UE.
- Base jurídica y finalidad documentadas.
- Minimización: no se ingiere lo que no se usa para el modelo.
- Derechos de acceso, rectificación y supresión operables.
- Contrato de encargado de tratamiento con clientes y subencargados.
- **Los datos de una empresa no entrenan modelos compartidos.** Declararlo explícitamente, como hace Armqu, es argumento comercial.

### 22.3 Uso de IA con datos financieros

- Enviar al LLM **resúmenes estructurados**, no volcados de datos brutos.
- Minimizar identificadores en los prompts.
- Registro de qué contexto se envió en cada interacción.
- Política clara de retención del proveedor de IA.
- Posibilidad de modelo autoalojado para clientes que lo exijan (fase posterior).

### 22.4 Cumplimiento por fases

| Fase | Nivel |
|---|---|
| MVP / piloto | Buenas prácticas, RGPD, audit trail, cifrado |
| Comercial inicial | DPA formal, política de retención, pentest básico |
| Escala | SOC 2 / ISO 27001 si el mercado lo exige |

Diseño "audit-friendly" desde el primer día; certificación cuando haya clientes que la pidan.

---

## 23. Calidad y testing

El motor financiero necesita un estándar de pruebas superior al del resto del sistema.

### 23.1 Niveles de prueba del motor

**Nivel 1 — Unitarios**
Cada cálculo con casos resueltos a mano: cuadro de amortización francés, VAN de una serie conocida, TIR de un flujo con solución analítica, amortización lineal, desfase de cobro.

**Nivel 2 — Golden tests**
Casos completos de empresa con resultados verificados contra un Excel de referencia construido de forma independiente. Si el motor cambia y un golden test se mueve, hay que justificarlo.

**Nivel 3 — Invariantes (property-based)**
Propiedades que deben cumplirse con cualquier entrada válida:
- El balance cuadra en todos los períodos.
- Suma de flujos netos = variación de la caja.
- Amortización acumulada ≤ coste del activo.
- Suma de cuotas de un préstamo = principal + intereses totales.
- VAN con tasa 0 = suma simple de flujos − inversión.
- Un escenario sin overrides da el mismo resultado que el base.

**Nivel 4 — Reconstrucción histórica**
Alimentar el motor con datos reales de una empresa y comprobar que reproduce sus estados financieros históricos dentro de un margen declarado. **Esta es la prueba que valida el TFG.**

### 23.2 Pruebas de la capa de IA

- Conjunto de enunciados en lenguaje natural → clasificación esperada de Decision Pack.
- Verificación de que ninguna cifra del texto generado difiere de la del motor.
- Casos adversariales: preguntas ambiguas, datos imposibles, intentos de hacer que estime.

### 23.3 Determinismo y reproducibilidad

- Hash de entradas en cada `calculation_run`: mismo hash debe dar mismo resultado.
- Versión del motor registrada con cada resultado.
- Semilla registrada en simulaciones estocásticas.
- Test de regresión que recalcula ejecuciones históricas y compara.

---

## 24. Métricas de producto

### 24.1 North star

> **Número de decisiones de capital registradas con su seguimiento cerrado.**

Mide las tres cosas a la vez: que se simula, que se decide y que se vuelve a mirar. Un producto con muchos escenarios y ningún seguimiento es un juguete.

### 24.2 Métricas de activación

| Métrica | Objetivo |
|---|---|
| Tiempo hasta el primer escenario | < 30 min |
| % de empresas que completan el modelo inicial | > 70 % |
| % que simulan una decisión en la primera semana | > 50 % |
| Calidad media del modelo tras onboarding | ≥ "media" |

### 24.3 Métricas de uso

- Escenarios creados por empresa y mes.
- Decisiones registradas por empresa y año.
- % de decisiones con motivo y alternativas rellenados.
- Uso de sensibilidad inversa (indicador de uso avanzado).
- Informes exportados (y cuántos a banco/socio).
- Señales del Risk Radar atendidas.

### 24.4 Métricas de valor

| Métrica | Qué indica |
|---|---|
| % de decisiones con seguimiento cerrado a 6 meses | Que el bucle Twin funciona |
| **Reducción del sesgo de previsión en el tiempo** | El indicador científico del producto |
| Nº de riesgos detectados antes de materializarse | Valor preventivo |
| Decisiones modificadas tras ver el escenario calibrado | Impacto real en el comportamiento |

La reducción del sesgo de previsión es la métrica más interesante: es medible, es defendible académicamente y es una promesa comercial honesta.

### 24.5 Métricas de negocio (más adelante)

Retención a 6 y 12 meses, expansión dentro de asesorías, empresas por asesoría, coste de adquisición. **No son prioridad ahora.**

---

## 25. Alcance del MVP

### 25.1 Must have (sin esto no hay producto)

**Datos y modelo**
- Importación Excel/CSV con plantilla propia.
- Importación de exportación contable con mapeo asistido.
- Modelo reducido: operación + finanzas + financiación.
- Unidades de negocio.
- Hipótesis como entidades con origen y confianza.
- Políticas de empresa.
- Versionado del modelo.
- Informe de calidad de datos.

**Motor**
- P&L mensual.
- Cash flow mensual (método directo, con desfases de cobro/pago).
- Balance simplificado.
- Cuadros de amortización de préstamos (francés, lineal, bullet, con carencia).
- Amortización de activos.
- IVA e impuesto de sociedades simplificados.
- VAN, TIR, payback simple y descontado.
- Ratios principales.
- Necesidad de financiación.
- Trazabilidad completa de cada resultado.

**Análisis**
- Escenarios por diferencias (base, conservador, adverso, custom).
- Comparación de escenarios.
- Sensibilidad directa (tornado).
- **Sensibilidad inversa** ("¿qué tendría que pasar?").
- Stress tests predefinidos.
- Comprobación de políticas.

**Decisión**
- 6 Decision Packs: establecimiento, financiación, activo, contratación, inversión genérica, plan de liquidez.
- Registro completo de decisiones (incluido motivo, responsable, alternativas, riesgos aceptados).
- Decision History consultable.
- Captura de resultados reales y cálculo de desviaciones.
- Perfil de sesgos básico con umbrales de confianza.
- Escenario calibrado por similitud histórica.

**IA**
- Orquestador con herramientas tipadas.
- Clasificación de intención → Decision Pack.
- Recopilación conversacional de datos faltantes.
- Propuesta de valores por defecto desde el modelo.
- Explicación de resultados.
- Redacción de informes con validación de cifras.

**Interfaz e informes**
- Home con situación, políticas y riesgos.
- Decision Studio.
- Editor del modelo.
- Proyecciones (P&L, cash flow, ratios).
- Decision History.
- Informe ejecutivo en PDF.
- Informe banco/socio en PDF.
- Plan vs real.

**Trust**
- Audit trail.
- Linaje de datos.
- Desglose de trazabilidad en cualquier cifra.
- Roles y permisos.

### 25.2 Should have (si el tiempo lo permite)

- Risk Radar con reglas básicas.
- Comparador de alternativas de financiación.
- Advisor Workspace mínimo (multi-empresa).
- Goal seek.
- Plantillas de mapeo reutilizables.
- Más Decision Packs (precios, comprar vs alquilar, refinanciación).

### 25.3 Could have (evolución)

- Monte Carlo.
- Agentes especializados.
- Conectores API (Holded, Odoo, PSD2).
- Benchmarks sectoriales anónimos.
- Detección de riesgos por ML.
- Modelo detallado de inventario y personal.
- Fiscalidad avanzada.
- Multi-empresa / consolidación.

### 25.4 Won't have (explícitamente fuera)

- Contabilidad o facturación.
- Conciliación bancaria.
- Gestión de cobros.
- Nóminas.
- Multi-divisa y multi-país.
- Decisión automática sin intervención humana.
- Asesoramiento fiscal o legal.

Declarar lo que **no** se hace es tan importante como lo que sí: evita el scope creep y define el posicionamiento.

---

## 26. Roadmap

### Fase 0 — Fundación (MVP)
**Objetivo:** modelo + motor + Decision Studio + History funcionando sobre una empresa real.

- Motor financiero con batería de pruebas.
- Modelo reducido e importación Excel.
- 6 Decision Packs.
- Escenarios, sensibilidad directa e inversa, stress.
- Decision History con registro completo.
- Plan vs real manual.
- Informes ejecutivo y banco.
- Trazabilidad y audit trail.

**Criterio de salida:** una pyme real puede simular una decisión de capital de principio a fin y obtener un informe que defendería ante su banco.

### Fase 1 — Producto recurrente
**Objetivo:** que la empresa vuelva cada mes.

- Risk Radar operativo.
- Chat guiado completo.
- Alertas de liquidez y endeudamiento.
- Perfil de sesgos con varias decisiones acumuladas.
- Escenario calibrado consolidado.
- Advisor Workspace.
- Más Decision Packs.
- Seguimiento mensual semiautomático.

### Fase 2 — Twin de verdad
**Objetivo:** el modelo se actualiza sin trabajo manual.

- Conectores Holded/Odoo + banco PSD2.
- Actualización automática del modelo.
- Agentes especializados.
- Recomendación de alternativas.
- Descomposición automática de desviaciones.
- Modelo de inventario y personal detallado.

### Fase 3 — Moat
**Objetivo:** ventajas que no se copian.

- Monte Carlo y análisis probabilístico.
- Calibración avanzada y por sector.
- Benchmarks anónimos entre pymes.
- Integraciones ERP.
- Packs sectoriales específicos.
- API pública para asesorías.

---

# BLOQUE IV — EJECUCIÓN

## 27. Validación y encaje con el TFG

### 27.1 Qué NO se intenta demostrar

> ❌ "Finance Twin mejora las decisiones empresariales."

Inalcanzable con rigor: requeriría grupo de control, muchas empresas y años. Afirmarlo debilitaría el trabajo.

### 27.2 Preguntas de validación (lo que sí se demuestra)

**V1 — Fidelidad del modelo**
*¿El modelo reproduce correctamente la situación financiera histórica de la empresa?*
Método: cargar 24–36 meses reales y comparar P&L, cash flow y balance generados con los reales. Métrica: desviación porcentual por partida y período, con margen declarado.

**V2 — Capacidad de proyección**
*¿Puede proyectar razonablemente el cash flow bajo hipótesis dadas?*
Método: backtesting. Situarse 12 meses atrás, proyectar con la información disponible entonces, comparar con lo ocurrido. Métricas: MAPE del saldo de caja, acierto en el mes de mínimo de caja.

**V3 — Corrección de instrumentos financieros**
*¿Representa correctamente préstamos, activos e inversiones?*
Método: comparar cuadros de amortización generados con los reales de la entidad financiera; verificar VAN/TIR contra cálculo independiente.

**V4 — Reconstrucción de decisiones**
*¿Pueden las decisiones históricas reales reconstruirse como escenarios?*
Método: tomar 3–5 decisiones pasadas de la empresa, reconstruirlas con la información que había entonces y comprobar que el sistema las representa.

**V5 — Detección de desviaciones**
*¿Detecta y cuantifica correctamente las desviaciones plan-real?*
Método: sobre las decisiones de V4, comparar la desviación calculada con la real conocida.

**V6 — Utilidad percibida**
*¿Los usuarios consideran útil el proceso?*
Método: sesiones con gerente y asesor; cuestionario estructurado (utilidad, comprensión, confianza, intención de uso); registro de qué cambió en su manera de ver la decisión.

**V7 — Fiabilidad de la capa de IA**
*¿La IA interpreta correctamente y nunca produce cifras?*
Método: batería de enunciados con clasificación esperada; verificación automática de que toda cifra en texto generado coincide con el motor.

### 27.3 Mapa TFG ↔ producto

| Dimensión del TFG | Artefacto |
|---|---|
| **Modelización financiera (ADE)** | Modelo de dominio, motor, instrumentos, métricas |
| **Arquitectura de software (Informática)** | Capas, motor independiente, API, trazabilidad |
| **Inteligencia artificial** | Orquestación con herramientas, control de alucinación |
| **Simulación y análisis** | Escenarios, sensibilidad directa e inversa, stress |
| **Investigación / aportación** | Decision History y calibración de sesgos en pymes |
| **Validación empírica** | V1–V7 sobre empresa real |
| **Visión de negocio** | Posicionamiento, ICP, competencia, modelo SaaS B2B |
| **Caso real** | Empresa piloto |

### 27.4 Aportación diferencial del TFG

Lo más original no es "una app financiera con IA". Es:

> **Un método para calibrar las hipótesis de decisión de una pyme a partir del historial de desviaciones de sus propias decisiones anteriores, integrado en un gemelo financiero con motor determinista y trazabilidad completa.**

Eso es defendible, medible y poco explorado en pymes.

### 27.5 Título propuesto

> *Diseño y desarrollo de una plataforma inteligente de simulación y planificación financiera para pymes basada en un gemelo digital empresarial.*

---

## 28. Validación con empresa piloto (discovery)

### 28.1 Principio

**No se congela el alcance antes de hablar con la empresa.** El documento de 2–3 páginas que se le presenta es comercial, no técnico: nada de arquitectura, capas ni agentes.

### 28.2 Guion del documento para la empresa

```
FINANCE TWIN
¿Qué le pasaría a tu empresa si...?

  · abres una tienda
  · pides un préstamo
  · compras un vehículo o maquinaria
  · amplías el almacén
  · contratas personal
  · haces una inversión importante

Finance Twin utiliza los datos de tu empresa para simular estas
decisiones ANTES de tomarlas, y te muestra su impacto sobre:

  · liquidez          · cash flow        · inversión
  · deuda             · rentabilidad     · capacidad de financiación

Y después compara lo previsto con lo que realmente pasó, para que
las siguientes decisiones partan de mejor información.
```

Y la pregunta que de verdad importa:

> **"Nos gustaría saber si esto resolvería un problema real para vosotros, y qué decisiones concretas os gustaría poder simular."**

### 28.3 Preguntas de discovery

**Sobre decisiones**
1. ¿Qué decisiones de dinero importante tenéis sobre la mesa en los próximos 12–24 meses?
2. ¿Cuáles tomasteis en los últimos tres años? ¿Cuánto comprometieron?
3. ¿Cómo las evaluasteis? ¿Quién hizo los números?
4. ¿Alguna salió claramente distinta de lo esperado? ¿En qué?
5. ¿Alguien volvió a mirar las previsiones después?

**Sobre proceso**
6. ¿Quién decide finalmente? ¿Quién tiene que estar de acuerdo?
7. ¿Qué papel juega la gestoría/asesor?
8. ¿Habéis tenido que pedir financiación? ¿Qué os pidió el banco?

**Sobre datos**
9. ¿Qué sistema de contabilidad/facturación usáis?
10. ¿Tenéis histórico de al menos dos años accesible?
11. ¿Lleváis control de caja previsional? ¿Cómo?
12. ¿Separáis por tienda / línea / unidad?

**Sobre dolor y valor**
13. ¿Qué es lo que más os gustaría saber antes de decidir y hoy no sabéis?
14. ¿Habéis dejado de hacer algo por no estar seguros del impacto?
15. Si existiera esto, ¿quién lo usaría y con qué frecuencia?

### 28.4 Qué hay que salir sabiendo

- 2–3 decisiones concretas y reales para usar como caso.
- Qué datos existen de verdad y en qué estado.
- Quién sería el usuario y quién el decisor.
- Si el informe para banco/socios es un gancho real.
- Si hay decisiones históricas documentadas para validar V4 y V5.

### 28.5 Después del discovery

1. Congelar el MVP alrededor de las decisiones que la empresa realmente tiene.
2. Priorizar los Decision Packs según eso.
3. Cerrar el protocolo de validación con los datos disponibles.
4. Empezar a construir.

---

## 29. Riesgos y mitigaciones

### 29.1 Riesgos de producto

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Scope creep** (intentar construir toda la visión) | Alto — es el que mata TFGs y productos | Este documento separa MVP / fases. El filtro de los cinco verbos. Won't-have explícito |
| **Datos insuficientes o sucios** | Alto — sin datos el twin es un Excel | Plantilla propia, mapeo asistido, informe de calidad visible, degradación honesta |
| **Modelo demasiado ambicioso** | Medio-alto | Grafo reducido primero; profundidad por vertical |
| **Nadie cierra el bucle plan-real** | Alto — sin bucle no hay Twin ni retención | Hitos programados, recordatorios, captura de reales lo más ligera posible |
| **El chat promete más de lo que da** | Medio | Decision Packs como camino principal; chat como puerta |
| **Arranque en frío del historial** | Medio | Reconstruir decisiones pasadas en onboarding; benchmarks sectoriales después |

### 29.2 Riesgos técnicos

| Riesgo | Mitigación |
|---|---|
| Error en el motor financiero | Cuatro niveles de prueba, invariantes, golden tests, reconstrucción histórica |
| Alucinación de la IA en cifras | Separación estricta, plantillas rellenadas por el motor, validación de salida |
| Circularidad en el cálculo (déficit → deuda → intereses) | Resolución iterativa explícita, con tope y convergencia declarada |
| Pérdida de reproducibilidad | Versionado de motor y modelo, hash de entradas, semillas registradas |
| Rendimiento con análisis masivos | Cálculo asíncrono, caché por hash de entradas |

### 29.3 Riesgos de mercado

| Riesgo | Mitigación |
|---|---|
| Holded/Agicap añaden simulación de inversiones | Nuestro moat no es el cálculo: es Decision History + calibración + trazabilidad |
| FounderConsole baja a pyme tradicional | Modelo de dominio y canal distintos; España y asesorías |
| La pyme no percibe el problema | Entrar por el momento de dolor: necesito financiación / voy a invertir |
| Ciclo de venta largo | Canal de asesorías; informe para banco como gancho urgente |
| El asesor lo ve como amenaza | Advisor Workspace: convertirlo en canal, no en competidor |

### 29.4 Riesgos del TFG

| Riesgo | Mitigación |
|---|---|
| "Esto ya existe" | Sección 5: estado del arte riguroso y formulación correcta del hueco |
| Validación débil | V1–V7 con métodos concretos y métricas declaradas |
| Demasiada amplitud, poca profundidad | Entregar MVP sólido + arquitectura completa documentada |
| La empresa piloto se cae | Protocolo de validación ejecutable con datos sintéticos realistas como plan B |

---

## 30. Modelo de negocio (deliberadamente diferido)

No hay prisa en lanzar ni en fijar precios. Se registran solo las hipótesis para no perderlas.

### 30.1 Hipótesis de empaquetado

| Plan | Para quién | Contenido tentativo |
|---|---|---|
| **Starter** | Pyme pequeña | 1 empresa, importación Excel, cash flow, escenarios básicos |
| **Decision** | Pyme con decisiones de capital | Decision Packs, sensibilidad, informes, plan vs real, History |
| **Advisor** | Asesorías | Multi-empresa, plantillas, marca propia |
| **Add-ons** | — | Monte Carlo, conectores bancarios, benchmarks |

### 30.2 Principio de precio

Cobrar por **empresa modelada y valor de decisión**, no por usuario ni por asiento contable. Un gerente que evita un error de 100.000 € no discute 200 €/mes; lo que no tolera es pagar por complejidad que no usa.

### 30.3 Qué hay que saber antes de poner precio

1. Qué decisión concreta están dispuestos a pagar por simular.
2. Si el informe para banco justifica el precio por sí solo.
3. Si la asesoría quiere revender o solo usar.
4. Cuánto cuesta realmente el onboarding de una empresa.

**Hasta entonces, no se fija pricing.**

---

## 31. Resumen en una página (para presentar)

```
FINANCE TWIN
Financial Decision Platform for SMEs

PROBLEMA
  La pyme decide el dinero grande con Excel, intuición y el asesor
  a posteriori. No modela la caja, no prepara el escenario adverso,
  no registra el porqué y no aprende de sus desviaciones.

SOLUCIÓN
  Un gemelo financiero de la empresa sobre el que simular decisiones
  antes de ejecutarlas, con números auditables, y un historial que
  calibra las hipótesis con la realidad.

CLAIM
  Antes de gastar 300.000 €, pruébalo aquí.

POR QUÉ AHORA
  Los datos de la pyme ya están digitalizados. La IA abarata la
  interfaz. El concepto está legitimado en gran empresa y nadie lo
  ha bajado a la pyme.

POR QUÉ NOSOTROS
  No somos tesorería ni FP&A enterprise. Somos la capa de decisión
  de capital para la pyme tradicional, con motor determinista y
  trazabilidad total.

PRINCIPIO
  La IA interpreta. El motor calcula.

MOAT
  Decision History de la empresa + calibración de sesgos +
  trazabilidad + canal de asesorías.

CUÑA DE ENTRADA
  "Voy a abrir un segundo local" / "necesito pedir un préstamo":
  informe defendible ante el banco en 20 minutos.

NO SOMOS
  Contabilidad. ERP. Otro software de tesorería. ChatGPT con números.
```

---

## 32. Glosario

| Término | Definición |
|---|---|
| **Company Twin** | Modelo estructurado y conectado de la empresa |
| **Decision Pack** | Plantilla de decisión con inputs, lógica, outputs e informe |
| **Decision Studio** | Entorno donde se construyen, analizan y registran decisiones |
| **Decision History** | Historial de decisiones con hipótesis, motivo y resultado real |
| **Twin Loop** | Ciclo previsión → decisión → realidad → desviación → calibración |
| **BiasProfile** | Perfil de desviaciones sistemáticas de las previsiones de una empresa |
| **Escenario calibrado** | Escenario con hipótesis ajustadas por los sesgos históricos |
| **Sensibilidad inversa** | Búsqueda del valor umbral que hace fracasar una decisión |
| **Guardrail / Política** | Límite configurado por la empresa que el sistema verifica |
| **Risk Radar** | Detección proactiva de situaciones que requieren atención |
| **Trust Layer** | Capa transversal de trazabilidad, versionado y auditoría |
| **Assumption** | Hipótesis como entidad con valor, origen, confianza y rango |
| **Golden test** | Caso de prueba con resultado verificado independientemente |
| **DSCR** | Ratio de cobertura del servicio de la deuda |
| **VAN / TIR** | Valor actual neto / tasa interna de retorno |
| **MAPE** | Error porcentual absoluto medio (métrica de precisión de previsión) |

---

## 33. Siguientes pasos

| # | Acción | Estado |
|---|---|---|
| 1 | Documento maestro de producto | ✅ Este documento |
| 2 | Documento comercial de 2–3 páginas para la empresa piloto | Pendiente |
| 3 | Sesión de discovery con la empresa | Pendiente |
| 4 | Congelar alcance del MVP según el discovery | Pendiente |
| 5 | Especificación del motor financiero (`docs/MOTOR_FINANCIERO.md`) | Pendiente |
| 6 | Modelo de datos detallado (`docs/MODELO_DATOS.md`) | Pendiente |
| 7 | Especificación de los 6 Decision Packs (`docs/DECISION_PACKS.md`) | Pendiente |
| 8 | Protocolo de validación V1–V7 (`docs/VALIDACION.md`) | Pendiente |
| 9 | Esqueleto del motor + primeras pruebas | Pendiente |
| 10 | API y modelo de datos | Pendiente |
| 11 | Interfaz y primer Decision Pack end-to-end | Pendiente |

---

## 34. Registro de decisiones

Toda decisión relevante de producto o arquitectura se registra aquí. Si no está escrito, no está decidido.

| # | Fecha | Decisión | Motivo |
|---|---|---|---|
| D01 | 2026-10-02 | El producto se plantea como producto B2B real; el TFG es el vehículo | Mayor ambición y coherencia con el perfil ADE + Informática |
| D02 | 2026-10-02 | Categoría comercial: *Financial Decision Platform for SMEs*; "Finance Twin" como concepto técnico | "Decision Finance Twin" es confuso comercialmente |
| D03 | 2026-10-02 | Principio no negociable: la IA interpreta, el motor calcula | Confianza, auditabilidad y defensa académica |
| D04 | 2026-10-02 | El MVP usa un **grafo reducido** (operación, finanzas, financiación), no el modelo completo | Permite una primera versión realmente funcional |
| D05 | 2026-10-02 | Decision History con **motivo y alternativas descartadas** es pieza de primer nivel, no accesoria | Es el activo diferencial y el moat real |
| D06 | 2026-10-02 | Monte Carlo queda fuera del MVP; sensibilidad inversa entra | Para una pyme, los umbrales críticos valen más que la distribución |
| D07 | 2026-10-02 | Un orquestador con herramientas en el MVP; agentes especializados después | Varios agentes sin motor robusto es teatro arquitectónico |
| D08 | 2026-10-02 | El motor se construye como librería Python independiente | Testeabilidad, auditabilidad y defensa en el TFG |
| D09 | 2026-10-02 | El TFG **no** intentará demostrar mejora de decisiones empresariales; validará V1–V7 | Rigor alcanzable |
| D10 | 2026-10-02 | Pricing y lanzamiento se posponen hasta después del discovery | Falta saber qué decisión se paga por simular |
| D11 | 2026-10-02 | ICP inicial estrecho: pyme tradicional española 0,5–15 M€ con decisiones de capital | Evitar competir donde ya hay producto consolidado |
| D12 | 2026-10-02 | Canal prioritario a explorar: asesorías y gestorías | Acceso eficiente a cartera de pymes en España |

---

*Documento vivo. Cualquier cambio de rumbo se refleja aquí antes de ejecutarse.*
