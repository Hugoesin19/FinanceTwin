"""P9 — calidad factual del twin (checklist; sin scores inventados)."""

from __future__ import annotations

from typing import Any


def assess_twin_quality(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """Devuelve checks booleanos y mensajes humanos. No inventa métricas financieras."""
    snap = snapshot or {}
    company = snap.get("company") or {}
    fiscal = snap.get("fiscal") or {}
    policies = snap.get("policies") or {}
    revenues = snap.get("revenue_streams") or []
    costs = snap.get("cost_items") or []
    if not isinstance(revenues, list):
        revenues = []
    if not isinstance(costs, list):
        costs = []

    checks: list[dict[str, Any]] = []

    def add(ok: bool, code: str, label: str, detail: str = "") -> None:
        checks.append(
            {"ok": bool(ok), "code": code, "label": label, "detail": detail}
        )

    opening = company.get("opening_cash")
    add(
        opening is not None and str(opening).strip() != "",
        "opening_cash",
        "Caja inicial definida",
        f"Valor: {opening}" if opening is not None else "Falta opening_cash",
    )
    add(
        policies.get("min_cash") is not None and str(policies.get("min_cash")).strip() != "",
        "min_cash_policy",
        "Política de caja mínima",
        f"Valor: {policies.get('min_cash')}",
    )
    add(
        fiscal.get("vat_rate") is not None,
        "vat_rate",
        "IVA configurado",
        f"Valor: {fiscal.get('vat_rate')}",
    )
    add(
        len(revenues) >= 1,
        "revenue_streams",
        "Al menos un ingreso recurrente",
        f"{len(revenues)} stream(s)",
    )
    add(
        len(costs) >= 1,
        "cost_items",
        "Al menos un coste",
        f"{len(costs)} coste(s)",
    )

    ready = {
        "new_site": bool(opening is not None and str(opening).strip() != ""),
        "financing": bool(opening is not None),
        "asset_purchase": bool(opening is not None),
        "hiring": bool(opening is not None),
        "generic_investment": bool(opening is not None),
        "liquidity_plan": len(revenues) >= 1 and len(costs) >= 1,
    }

    missing_human = [c["label"] for c in checks if not c["ok"]]
    return {
        "checks": checks,
        "ready_for_packs": ready,
        "summary": {
            "revenue_stream_count": len(revenues),
            "cost_item_count": len(costs),
            "issues_count": len(missing_human),
            "issues": missing_human,
        },
    }
