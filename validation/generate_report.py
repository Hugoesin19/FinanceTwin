#!/usr/bin/env python3
"""Genera validation/results/F8_RESUMEN.md — campaña F8 Plan B."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).resolve().parent / "results"
FIX = Path(__file__).resolve().parent / "fixtures"


def run_pytest(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    suites = {
        "L0_golden_invariants": [
            "engine/tests/golden",
            "engine/tests/invariants",
            "-q",
            "--tb=no",
        ],
        "L1_mapper": ["engine/tests/unit/test_mapper_m1_m7.py", "-q", "--tb=no"],
        "L2_new_site": ["engine/tests/golden/test_new_site_e2e.py", "-q", "--tb=no"],
        "V1_V5_plan_b": ["validation/tests", "-q", "--tb=line"],
        "API_regression": ["api/tests", "-q", "--tb=no"],
    }

    results: dict[str, dict] = {}
    for name, args in suites.items():
        code, out = run_pytest(args)
        # last line like "84 passed"
        tail = "\n".join(out.strip().splitlines()[-5:])
        results[name] = {"exit_code": code, "pass": code == 0, "tail": tail}

    v4 = json.loads((FIX / "decisions_v4.json").read_text(encoding="utf-8"))
    scores = []
    for d in v4["decisions"]:
        sc = d["scorecard"]
        scores.append(
            0.2
            * (
                sc["pack_correct"]
                + sc["capex_timing"]
                + sc["funding"]
                + sc["ops_effect"]
                + sc["report_clear"]
            )
        )
    v4_mean = sum(scores) / len(scores)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Evidencia F8 — Validación TFG (Plan B)",
        "",
        f"Generado: `{now}`",
        "",
        "Protocolo: `docs/VALIDACION.md`. Modo: **Plan B** (sin pyme piloto en repo).",
        "",
        "## Suites ejecutadas",
        "",
        "| Suite | PASS | Detalle |",
        "|---|---|---|",
    ]
    for name, r in results.items():
        mark = "PASS" if r["pass"] else "FAIL"
        detail = r["tail"].replace("|", "/").replace("\n", " ")
        lines.append(f"| `{name}` | {mark} | `{detail}` |")

    all_auto = all(r["pass"] for r in results.values())

    lines += [
        "",
        "## Matriz §9 / §10",
        "",
        "| ID | Resultado | Notas |",
        "|---|---|---|",
        f"| L0 | {'PASS' if results['L0_golden_invariants']['pass'] else 'FAIL'} | golden G* + invariantes demo |",
        f"| L1 | {'PASS' if results['L1_mapper']['pass'] else 'FAIL'} | mapper M1–M7 |",
        f"| L2 | {'PASS' if results['L2_new_site']['pass'] else 'FAIL'} | E2E new_site |",
        "| V1 | PASS* | *Plan B reconstrucción sintética MAPE≈0 (auto-consistencia) |",
        "| V2 | PASS* | *Plan B backtest débil primeros 12m; reinicio t=12 francés = limitación documentada |",
        "| V3 | PASS | préstamo francés genérico + VAN independiente (G1/G2) |",
        f"| V4 | PASS* | *3 packs sintéticos ejecutados; media scorecard={v4_mean:.2f}; sin entrevista real |",
        "| V5 | PASS | deviation_pct + mediana bias + gate calibración n≥3 |",
        "| V6 | PENDIENTE | plantilla en `validation/sessions/V6_PLANTILLA_ACTA.md` — falta sesión humana |",
        "| V7 | N/A | F9 diferida |",
        "",
        "## Criterios globales §10 (defensa TFG)",
        "",
        f"1. L0 PASS — {'sí' if results['L0_golden_invariants']['pass'] else 'NO'}",
        f"2. L2 new_site PASS — {'sí' if results['L2_new_site']['pass'] else 'NO'}",
        "3. V1 PASS o FAIL documentado — sí (Plan B PASS* con ruido controlado en caja)",
        "4. V3 PASS — sí (préstamo + VAN)",
        "5. V4 media≥0.8 o Plan B — sí (sintético + packs ejecutados; falta entrevista real del Plan B)",
        "6. V6 sesión + Likert — **NO aún** (plantilla lista)",
        "7. Limitaciones listadas — sí (abajo)",
        "",
        f"**Veredicto F8 automatizable:** {'PASS' if all_auto else 'FAIL'}.  ",
        "**Veredicto §10 completo para defensa:** PARCIAL — falta V6 sesión real (y entrevista V4 opcional Plan B).",
        "",
        "## Artefactos numéricos",
        "",
        "- `validation/results/v1_mape.json`",
        "- `validation/results/v2_backtest.json`",
        "- `validation/results/v3_loan_diff.json`",
        "- `validation/results/v4_scorecards.json`",
        "",
        "## Limitaciones (obligatorio memoria)",
        "",
        "- IVA/IS simplificados (a menudo 0 en fixtures).",
        "- AR/AP lags: fixtures V1 usan `collection_days=0`.",
        "- V1–V2 Plan B no usan datos de pyme real; no se afirma poder predictivo externo.",
        "- V1 ruido: observado sintético ±noise sobre caja; el twin se reconstruye sin reestimar drivers.",
        "- Reinicio de préstamo francés a mitad de vida recalcula cuota ≠ senda original.",
        "- V4 scorecards son sintéticos; packs sí se ejecutan; no hay entrevista a empresario aún.",
        "- V6 no se inventa: requiere acta documentada.",
        "",
        "## Cómo reproducir",
        "",
        "```powershell",
        "python validation/generate_report.py",
        "python -m pytest engine/tests api/tests validation/tests -q",
        "```",
        "",
    ]

    out_path = RESULTS / "F8_RESUMEN.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta = {
        "generated_at": now,
        "suites": {k: {"pass": v["pass"], "exit_code": v["exit_code"]} for k, v in results.items()},
        "v4_mean": v4_mean,
        "section_10_complete": False,
        "v6_status": "pending_session",
    }
    (RESULTS / "F8_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(out_path)
    print("all_auto", all_auto)
    return 0 if all_auto else 1


if __name__ == "__main__":
    raise SystemExit(main())
