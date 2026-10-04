# Validación TFG — campaña F8

Protocolo: [`docs/VALIDACION.md`](../docs/VALIDACION.md)  
Modo: **Plan B** (sin empresa piloto en git; datos sintéticos + golden).

## Qué incluye

| ID | Contenido | Automatizado |
|---|---|---|
| L0 | pytest golden + invariantes | sí |
| L1 | tests mapper | sí |
| L2 | E2E `new_site` | sí |
| V1 | Fidelidad histórica sintética (reconstrucción) | sí |
| V2 | Backtest sintético 12m | sí |
| V3 | Préstamo francés + VAN/TIR independientes | sí |
| V4 | 3 decisiones sintéticas tipadas a packs (scorecards) | sí |
| V5 | ActualResult + BiasProfile (n≥3) | sí |
| V6 | Acta + Likert | **plantilla**; sesión humana pendiente |
| V7 | IA | N/A diferida (F9) |

## Cómo ejecutar

```powershell
cd D:\tfgade
python -m pip install -e engine -e "api[dev]" -q
python validation/generate_report.py
```

También:

```powershell
python -m pytest engine/tests api/tests validation/tests -q
```

Informe generado: `validation/results/F8_RESUMEN.md`

## Honestidad Plan B

V1–V2 no usan datos de pyme real: demuestran **auto-consistencia** del twin/motor y umbrales del protocolo bajo serie sintética. No se afirma mejora causal de decisiones (§0 VALIDACION).
