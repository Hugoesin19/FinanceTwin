# Inventario de documentación — Finance Twin

**Última actualización:** 3 octubre 2026

---

## Cómo trabajar (importante)

1. Abrir [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md) → ver **fase activa**  
2. Abrir la spec que esa fase cita  
3. Programar **solo** esa fase  
4. No inventar nada que no esté en specs  

Sin el plan de implementación, las specs describen el producto pero **no evitan** que el desarrollo se desvíe.

---

## 1. Documentos hechos

| Documento | Ruta | Rol |
|---|---|---|
| **Plan de implementación** | [`PLAN_IMPLEMENTACION.md`](PLAN_IMPLEMENTACION.md) | **Orden + reglas anti-alucinación + DoD** |
| Producto | [`PRODUCTO.md`](PRODUCTO.md) | Visión y alcance |
| Motor | [`MOTOR_FINANCIERO.md`](MOTOR_FINANCIERO.md) | Cálculo |
| Datos | [`MODELO_DATOS.md`](MODELO_DATOS.md) | Estructura de datos |
| Packs | [`DECISION_PACKS.md`](DECISION_PACKS.md) | Decisiones MVP |
| Validación | [`VALIDACION.md`](VALIDACION.md) | PASS/FAIL L0–L5 |
| Inventario | [`DOCUMENTACION.md`](DOCUMENTACION.md) | Este archivo |
| README | [`../README.md`](../README.md) | Presentación |
| API | [`API.md`](API.md) | Endpoints implementados (F5) |
| Arquitectura | [`ARQUITECTURA.md`](ARQUITECTURA.md) | Capas reales F0–F6 |

## 2. Local / privado

`docs/madagascar/` — gitignored

## 3. Pendientes / ADR

| Documento | Cuándo |
|---|---|
| `MVP_CHECKLIST.md` | Opcional: el checklist ya está dentro del PLAN §5 |

**ADRs:** [`adr/0001-loan-skip-drawdown-pre-anchor.md`](adr/0001-loan-skip-drawdown-pre-anchor.md)

## 4. Estado

```
Specs de contenido ........ HECHAS
Plan de implementación .... HECHO (fase activa: F8)
Código .................... F0–F7 HECHAS; F8 pendiente (validación TFG)
```

---

*Actualizar estados de fase en PLAN_IMPLEMENTACION.md al completar cada una.*
