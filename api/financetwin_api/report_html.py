"""P10 — informe ejecutivo HTML (solo pinta campos del CalculationRun / compare)."""

from __future__ import annotations

import html
from typing import Any


def _esc(v: Any) -> str:
    if v is None:
        return "—"
    return html.escape(str(v))


def _metric_rows(run: dict[str, Any]) -> str:
    im = run.get("investment_metrics") or {}
    fn = run.get("financing_need") or {}
    rows = [
        ("Valor creado (VAN)", im.get("npv")),
        ("Rentabilidad anual (TIR)", im.get("irr_annual")),
        ("Payback simple", im.get("payback_simple")),
        ("Payback descontado", im.get("payback_discounted")),
        ("Caja más baja", fn.get("min_cash")),
        ("Mes caja más baja", fn.get("min_cash_month")),
        ("Hueco vs política", fn.get("max_shortfall_vs_policy")),
        ("Primer mes en hueco", fn.get("first_shortfall_month")),
        ("Meses bajo política", fn.get("months_below_policy")),
    ]
    out = []
    for label, val in rows:
        out.append(f"<tr><th>{_esc(label)}</th><td>{_esc(val)}</td></tr>")
    return "\n".join(out)


def _policies(run: dict[str, Any]) -> str:
    rows = []
    for p in run.get("policy_checks") or []:
        rows.append(
            "<tr>"
            f"<td>{_esc(p.get('policy_id'))}</td>"
            f"<td>{_esc(p.get('status'))}</td>"
            f"<td>{_esc(p.get('value'))}</td>"
            f"<td>{_esc(p.get('threshold'))}</td>"
            f"<td>{_esc(p.get('message'))}</td>"
            "</tr>"
        )
    if not rows:
        return "<tr><td colspan='5'>Sin comprobaciones</td></tr>"
    return "\n".join(rows)


def _compare(compare: dict[str, Any] | None) -> str:
    if not compare:
        return "<p>Sin comparación de escenarios en este informe.</p>"
    paths = [
        ("VAN", ["investment_metrics", "npv"]),
        ("TIR", ["investment_metrics", "irr_annual"]),
        ("Caja más baja", ["financing_need", "min_cash"]),
        ("Hueco vs política", ["financing_need", "max_shortfall_vs_policy"]),
    ]

    def get(run: dict[str, Any], path: list[str]) -> Any:
        cur: Any = run
        for k in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    lines = [
        "<table><thead><tr><th>Indicador</th><th>Base</th>"
        "<th>Conservador</th><th>Adverso</th></tr></thead><tbody>"
    ]
    for label, path in paths:
        lines.append(
            "<tr>"
            f"<td>{_esc(label)}</td>"
            f"<td>{_esc(get(compare.get('base') or {}, path))}</td>"
            f"<td>{_esc(get(compare.get('conservative') or {}, path))}</td>"
            f"<td>{_esc(get(compare.get('adverse') or {}, path))}</td>"
            "</tr>"
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def render_executive_html(
    *,
    company_name: str,
    run: dict[str, Any],
    compare: dict[str, Any] | None = None,
) -> str:
    pack = run.get("pack_id") or "—"
    variant = run.get("variant") or "—"
    run_id = run.get("calculation_run_id") or "—"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Informe Finance Twin — {_esc(company_name)}</title>
  <style>
    body {{ font-family: Georgia, serif; color: #0f1c24; max-width: 860px; margin: 2rem auto; padding: 0 1rem; line-height: 1.45; }}
    h1 {{ font-size: 1.6rem; }}
    h2 {{ font-size: 1.15rem; margin-top: 1.6rem; border-bottom: 1px solid #c9d4dc; padding-bottom: 0.3rem; }}
    table {{ width: 100%; border-collapse: collapse; font-family: system-ui, sans-serif; font-size: 0.9rem; }}
    th, td {{ border-bottom: 1px solid #dde5eb; padding: 0.4rem 0.5rem; text-align: left; }}
    th {{ color: #5a6b75; font-weight: 600; }}
    .meta {{ color: #5a6b75; font-size: 0.9rem; }}
    .note {{ font-size: 0.85rem; color: #5a6b75; margin-top: 2rem; }}
  </style>
</head>
<body>
  <h1>Informe ejecutivo — Finance Twin</h1>
  <p class="meta">Empresa: {_esc(company_name)} · Pack: {_esc(pack)} · Escenario: {_esc(variant)} · Run: {_esc(run_id)}</p>
  <p class="meta">Los números proceden del motor financiero; este documento no recalcula.</p>

  <h2>Resumen</h2>
  <table>
    <tbody>
      {_metric_rows(run)}
    </tbody>
  </table>

  <h2>Políticas</h2>
  <table>
    <thead><tr><th>Política</th><th>Estado</th><th>Valor</th><th>Umbral</th><th>Mensaje</th></tr></thead>
    <tbody>
      {_policies(run)}
    </tbody>
  </table>

  <h2>Comparación de escenarios</h2>
  {_compare(compare)}

  <h2>Trazabilidad</h2>
  <table>
    <tbody>
      <tr><th>model_version_id</th><td>{_esc(run.get("model_version_id"))}</td></tr>
      <tr><th>scenario_id</th><td>{_esc(run.get("scenario_id"))}</td></tr>
      <tr><th>inputs_hash</th><td>{_esc(run.get("inputs_hash"))}</td></tr>
      <tr><th>result_hash</th><td>{_esc(run.get("result_hash"))}</td></tr>
      <tr><th>engine_version</th><td>{_esc(run.get("engine_version"))}</td></tr>
    </tbody>
  </table>

  <p class="note">Finance Twin — informe generado a partir de CalculationRun. No constituye asesoramiento fiscal o legal.</p>
</body>
</html>
"""
