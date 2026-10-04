# Evidencia F8 — Validación TFG (Plan B)

Generado: `2026-10-04 10:45 UTC`

Protocolo: `docs/VALIDACION.md`. Modo: **Plan B** (sin pyme piloto en repo).

## Suites ejecutadas

| Suite | PASS | Detalle |
|---|---|---|
| `L0_golden_invariants` | PASS | `............................                                             [100%] 28 passed in 0.22s` |
| `L1_mapper` | PASS | `.........                                                                [100%] 9 passed in 0.11s` |
| `L2_new_site` | PASS | `.....                                                                    [100%] 5 passed in 0.12s` |
| `V1_V5_plan_b` | PASS | `.......                                                                  [100%] 7 passed in 0.13s` |
| `API_regression` | PASS | `  C:\Users\USUARIO\AppData\Local\Programs\Python\Python311\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.     from starlette.testclient import TestClient as TestClient  # noqa  -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html 21 passed, 1 warning in 5.38s` |

## Matriz §9 / §10

| ID | Resultado | Notas |
|---|---|---|
| L0 | PASS | golden G* + invariantes demo |
| L1 | PASS | mapper M1–M7 |
| L2 | PASS | E2E new_site |
| V1 | PASS* | *Plan B reconstrucción sintética MAPE≈0 (auto-consistencia) |
| V2 | PASS* | *Plan B backtest débil primeros 12m; reinicio t=12 francés = limitación documentada |
| V3 | PASS | préstamo francés genérico + VAN independiente (G1/G2) |
| V4 | PASS* | *3 packs sintéticos ejecutados; media scorecard=0.97; sin entrevista real |
| V5 | PASS | deviation_pct + mediana bias + gate calibración n≥3 |
| V6 | PENDIENTE | plantilla en `validation/sessions/V6_PLANTILLA_ACTA.md` — falta sesión humana |
| V7 | N/A | F9 diferida |

## Criterios globales §10 (defensa TFG)

1. L0 PASS — sí
2. L2 new_site PASS — sí
3. V1 PASS o FAIL documentado — sí (Plan B PASS* con ruido controlado en caja)
4. V3 PASS — sí (préstamo + VAN)
5. V4 media≥0.8 o Plan B — sí (sintético + packs ejecutados; falta entrevista real del Plan B)
6. V6 sesión + Likert — **NO aún** (plantilla lista)
7. Limitaciones listadas — sí (abajo)

**Veredicto F8 automatizable:** PASS.  
**Veredicto §10 completo para defensa:** PARCIAL — falta V6 sesión real (y entrevista V4 opcional Plan B).

## Artefactos numéricos

- `validation/results/v1_mape.json`
- `validation/results/v2_backtest.json`
- `validation/results/v3_loan_diff.json`
- `validation/results/v4_scorecards.json`

## Limitaciones (obligatorio memoria)

- IVA/IS simplificados (a menudo 0 en fixtures).
- AR/AP lags: fixtures V1 usan `collection_days=0`.
- V1–V2 Plan B no usan datos de pyme real; no se afirma poder predictivo externo.
- V1 ruido: observado sintético ±noise sobre caja; el twin se reconstruye sin reestimar drivers.
- Reinicio de préstamo francés a mitad de vida recalcula cuota ≠ senda original.
- V4 scorecards son sintéticos; packs sí se ejecutan; no hay entrevista a empresario aún.
- V6 no se inventa: requiere acta documentada.

## Cómo reproducir

```powershell
python validation/generate_report.py
python -m pytest engine/tests api/tests validation/tests -q
```

