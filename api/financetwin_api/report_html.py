"""Informe ejecutivo HTML (solo pinta campos del CalculationRun / compare / analytics)."""

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


def _reading(run: dict[str, Any]) -> str:
    im = run.get("investment_metrics") or {}
    fn = run.get("financing_need") or {}
    fails = sum(1 for p in (run.get("policy_checks") or []) if p.get("status") == "fail")
    npv = im.get("npv")
    min_cash = fn.get("min_cash")
    if fails:
        return (
            f"<div class='callout warn'><strong>Trade-off:</strong> hay {fails} política(s) en fallo. "
            f"VAN={_esc(npv)} · caja más baja={_esc(min_cash)}. "
            "No decidas solo por rentabilidad si la liquidez se rompe.</div>"
        )
    return (
        f"<div class='callout ok'><strong>Lectura:</strong> políticas OK. "
        f"VAN={_esc(npv)} · caja más baja={_esc(min_cash)}.</div>"
    )


def _scorecard(scorecard: dict[str, Any] | None) -> str:
    if not scorecard:
        return ""
    return (
        "<h2>Scorecard de decisión</h2>"
        "<table><tbody>"
        f"<tr><th>Valor</th><td>{_esc(scorecard.get('valueScore'))}</td></tr>"
        f"<tr><th>Liquidez</th><td>{_esc(scorecard.get('liqScore'))}</td></tr>"
        f"<tr><th>Riesgo MC</th><td>{_esc(scorecard.get('riskScore'))}</td></tr>"
        f"<tr><th>Semáforo</th><td>{_esc(scorecard.get('overall'))}</td></tr>"
        "</tbody></table>"
    )


def _montecarlo(mc: dict[str, Any] | None) -> str:
    if not mc:
        return ""
    return (
        "<h2>Incertidumbre (Monte Carlo)</h2>"
        f"<p class='meta'>{_esc(mc.get('disclaimer'))}</p>"
        "<table><tbody>"
        f"<tr><th>Simulaciones</th><td>{_esc(mc.get('n_sims'))}</td></tr>"
        f"<tr><th>VAN P10</th><td>{_esc(mc.get('npv_p10'))}</td></tr>"
        f"<tr><th>VAN P50</th><td>{_esc(mc.get('npv_p50'))}</td></tr>"
        f"<tr><th>VAN P90</th><td>{_esc(mc.get('npv_p90'))}</td></tr>"
        f"<tr><th>% sims VAN&gt;0</th><td>{_esc(mc.get('prob_npv_positive'))}</td></tr>"
        f"<tr><th>% sims rompen caja mínima</th><td>{_esc(mc.get('prob_cash_breach'))}</td></tr>"
        "</tbody></table>"
    )


def render_executive_html(
    *,
    company_name: str,
    run: dict[str, Any],
    compare: dict[str, Any] | None = None,
    montecarlo: dict[str, Any] | None = None,
    scorecard: dict[str, Any] | None = None,
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
    .callout {{ padding: 0.75rem 1rem; border-radius: 8px; margin: 1rem 0; font-family: system-ui, sans-serif; }}
    .callout.ok {{ background: #e8f3ec; }}
    .callout.warn {{ background: #f7f1de; }}
  </style>
</head>
<body>
  <h1>Informe ejecutivo — Memo de decisión</h1>
  <p class="meta">Empresa: {_esc(company_name)} · Pack: {_esc(pack)} · Escenario: {_esc(variant)} · Run: {_esc(run_id)}</p>
  <p class="meta">Los números proceden del motor financiero; este documento no recalcula.</p>

  <h2>Lectura gerencial</h2>
  {_reading(run)}

  {_scorecard(scorecard)}

  <h2>Resumen de métricas</h2>
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

  {_montecarlo(montecarlo)}

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
