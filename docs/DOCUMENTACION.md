# Inventario de documentación — Finance Twin

**Última actualización:** 4 octubre 2026

---

## Cómo trabajar (importante)

1. Abrir [`PLAN_PRODUCTO.md`](PLAN_PRODUCTO.md) → ver **fase activa de producto** (P1+)  
2. Reglas anti-alucinación: [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md) §2 (R1–R10)  
3. Abrir la spec que esa fase cita  
4. Programar **solo** esa fase  
5. No inventar nada que no esté en specs  

Fundación F0–F8: [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md) (histórico; F9 IA diferida).

---

## 1. Documentos hechos

| Documento | Ruta | Rol |
|---|---|---|
| **Plan de producto (activo)** | [`PLAN_PRODUCTO.md`](PLAN_PRODUCTO.md) | **Orden P1+ UI/usabilidad + DoD** |
| Plan fundación F0–F8 | [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md) | Núcleo + reglas R1–R10 + F9 diferida |
| Producto | [`PRODUCTO.md`](PRODUCTO.md) | Visión y alcance |
| Motor | [`MOTOR_FINANCIERO.md`](MOTOR_FINANCIERO.md) | Cálculo |
| Datos | [`MODELO_DATOS.md`](MODELO_DATOS.md) | Estructura de datos |
| Packs | [`DECISION_PACKS.md`](DECISION_PACKS.md) | Decisiones MVP |
| Validación | [`VALIDACION.md`](VALIDACION.md) | PASS/FAIL L0–L5 |
| Evidencia F8 | [`../validation/results/F8_RESUMEN.md`](../validation/results/F8_RESUMEN.md) | Campaña Plan B |
| Inventario | [`DOCUMENTACION.md`](DOCUMENTACION.md) | Este archivo |
| README | [`../README.md`](../README.md) | Presentación |
| API | [`API.md`](API.md) | Endpoints implementados |
| Arquitectura | [`ARQUITECTURA.md`](ARQUITECTURA.md) | Capas reales |

## 2. Local / privado

`docs/madagascar/` — gitignored

## 3. Pendientes / ADR

| Documento | Cuándo |
|---|---|
| `IA_TOOLS.md` | Solo si se reactiva F9 |
| Plantilla import CSV | Con fase P5 |

**ADRs:** [`adr/0001-loan-skip-drawdown-pre-anchor.md`](adr/0001-loan-skip-drawdown-pre-anchor.md)

## 4. Estado

```
Specs de contenido ........ HECHAS
Plan fundación F0–F8 ...... HECHO (F9 diferida; V6 sesión pendiente)
Plan producto P1+ ......... P1–P15 HECHAS (flujo humano; F9/auth diferidas)
Código .................... Onboarding + demo narrada + números legibles; UI no calcula
```

---

*Actualizar estados de fase en PLAN_PRODUCTO.md al completar cada Px.*
