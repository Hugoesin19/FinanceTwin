"""Pack generic_investment — DECISION_PACKS §9."""

from __future__ import annotations

from typing import Any

from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper.build_ops import BuildOp
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot
from financetwin_engine.packs.base import (
    BuiltScenarioBundle,
    Issue,
    PackInput,
    VariantPlan,
    has_errors,
)
from financetwin_engine.packs.common import ZERO, d, savings_ops, stable_id
from financetwin_engine.packs import defaults as R

PACK_ID = "generic_investment"


class GenericInvestmentPack:
    id = PACK_ID

    def inputs_schema(self) -> list[PackInput]:
        return [
            PackInput("name", "Nombre", "text", True),
            PackInput("capex_schedule", "Calendario CAPEX", "json", True),
            PackInput("horizon_months", "Horizonte", "count", True),
            PackInput("benefit_cadence", "Cadencia beneficio", "enum", True, enum_values=("monthly", "annual")),
            PackInput("benefit_amount", "Importe beneficio", "money", True),
            PackInput("benefit_type", "Tipo beneficio", "enum", True, enum_values=("opex_reduction", "revenue")),
            PackInput("gross_margin_pct", "Margen", "rate", False),
            PackInput("cost_item_id_to_reduce", "Coste a reducir", "text", False),
            PackInput("debt_amount", "Deuda", "money", False),
            PackInput("equity_amount", "Equity", "money", False),
            PackInput("loan_annual_rate", "TIN", "rate", False),
            PackInput("loan_term_months", "Plazo", "count", False),
            PackInput("loan_grace_months", "Carencia", "count", False),
            PackInput("loan_grace_type", "Tipo carencia", "enum", False, enum_values=("capital", "total")),
            PackInput("discount_rate_annual", "Tasa descuento", "rate", True),
        ]

    def actual_keys(self) -> list[str]:
        return ["capex_total", "sales_monthly", "payback_months", "min_cash"]

    def resolve_defaults(self, snapshot: CompanyTwinSnapshot, user_partial: dict[str, Any]) -> dict[str, Any]:
        out = dict(user_partial)
        if "debt_amount" not in out:
            out["debt_amount"] = ZERO
        if "loan_grace_months" not in out:
            out["loan_grace_months"] = 0
        if "discount_rate_annual" not in out:
            out["discount_rate_annual"] = R.debt_cost_plus_premium(snapshot)
        if "benefit_type" in out and out["benefit_type"] == "revenue" and "gross_margin_pct" not in out:
            v = R.company_gross_margin(snapshot)
            if v is not None:
                out["gross_margin_pct"] = v
        # equity default to cover capex - debt
        if "equity_amount" not in out and "capex_schedule" in out:
            total = sum((d(p["amount"]) for p in out["capex_schedule"]), ZERO)
            debt = d(out.get("debt_amount"), ZERO)
            out["equity_amount"] = max(ZERO, total - debt)
        return out

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        for key in ("name", "capex_schedule", "horizon_months", "benefit_cadence", "benefit_amount", "benefit_type", "discount_rate_annual"):
            if key not in inputs or inputs[key] in (None, ""):
                issues.append(Issue("error", "missing_required", f"missing: {key}"))
        if has_errors(issues):
            return issues
        if inputs["benefit_cadence"] not in ("monthly", "annual"):
            issues.append(Issue("error", "bad_cadence", "benefit_cadence monthly|annual"))
        if inputs["benefit_type"] not in ("opex_reduction", "revenue"):
            issues.append(Issue("error", "bad_benefit", "benefit_type invalid"))
        if inputs["benefit_type"] == "revenue" and inputs.get("gross_margin_pct") is None:
            issues.append(Issue("error", "missing_margin", "gross_margin_pct required for revenue benefit"))
        sched = inputs["capex_schedule"]
        if not isinstance(sched, (list, tuple)) or len(sched) < 1:
            issues.append(Issue("error", "empty_capex", "capex_schedule required"))
        debt = d(inputs.get("debt_amount"), ZERO)
        if debt > ZERO:
            if inputs.get("loan_annual_rate") is None or inputs.get("loan_term_months") is None:
                issues.append(Issue("error", "missing_loan", "loan rate/term required when debt>0"))
            total = sum((d(p["amount"]) for p in sched), ZERO)
            equity = d(inputs.get("equity_amount"), ZERO)
            if debt + equity < total:
                issues.append(
                    Issue("error", "funding_insufficient", "debt+equity < total capex")
                )
        return issues

    def build(self, snapshot: CompanyTwinSnapshot, inputs: dict[str, Any]) -> BuiltScenarioBundle:
        resolved = self.resolve_defaults(snapshot, inputs)
        issues = self.validate_inputs(resolved)
        if has_errors(issues):
            raise ValueError("; ".join(i.message for i in issues if i.severity == "error"))

        variants: dict[str, VariantPlan] = {}
        for vname, ben_f, cap_f in (
            ("base", "1", "1"),
            ("conservative", "0.85", "1"),
            ("adverse", "0.70", "1.10"),
        ):
            adj = dict(resolved)
            adj["benefit_amount"] = d(resolved["benefit_amount"]) * D(ben_f)
            adj["capex_schedule"] = [
                {
                    **pt,
                    "amount": str(d(pt["amount"]) * D(cap_f)),
                }
                for pt in resolved["capex_schedule"]
            ]
            # bump equity if adverse capex grows
            total = sum((d(p["amount"]) for p in adj["capex_schedule"]), ZERO)
            debt = d(adj.get("debt_amount"), ZERO)
            equity = d(adj.get("equity_amount"), ZERO)
            if debt + equity < total:
                adj["equity_amount"] = total - debt
            ops, meta = self._ops(snapshot, adj, vname)
            variants[vname] = VariantPlan(name=vname, build_ops=ops, **meta)

        return BuiltScenarioBundle(pack_id=PACK_ID, variants=variants, resolved_inputs=resolved)

    def _ops(
        self,
        snapshot: CompanyTwinSnapshot,
        inputs: dict[str, Any],
        variant: str,
    ) -> tuple[tuple[BuildOp, ...], dict[str, Any]]:
        name = str(inputs["name"])
        sched = inputs["capex_schedule"]
        first_ym = str(sched[0]["year_month"])
        horizon = int(inputs["horizon_months"])
        inv_id = stable_id("inv", name, variant)
        ops: list[BuildOp] = []

        debt = d(inputs.get("debt_amount"), ZERO)
        equity = d(inputs.get("equity_amount"), ZERO)
        loan_id = None
        linked_loans: list[str] = []
        if debt > ZERO:
            loan_id = stable_id("loan", name, variant)
            linked_loans = [loan_id]
            grace = int(inputs.get("loan_grace_months") or 0)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="loans",
                    entity_id=loan_id,
                    payload={
                        "id": loan_id,
                        "name": f"Loan {name}",
                        "principal": str(debt),
                        "annual_interest_rate": str(d(inputs["loan_annual_rate"])),
                        "term_months": int(inputs["loan_term_months"]),
                        "amortization_system": "french",
                        "grace_months": grace,
                        "grace_type": (inputs.get("loan_grace_type") if grace > 0 else "none"),
                        "disbursement_year_month": first_ym,
                        "origination_fee": "0",
                        "rate_type": "fixed",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )

        inv_payload: dict[str, Any] = {
            "id": inv_id,
            "name": name,
            "decision_pack_id": PACK_ID,
            "capex_schedule": [
                {
                    "year_month": str(pt["year_month"]),
                    "amount": str(d(pt["amount"])),
                    "includes_vat": bool(pt.get("includes_vat", False)),
                }
                for pt in sched
            ],
            "linked_loan_ids": linked_loans,
            "analysis_start_year_month": first_ym,
            "analysis_horizon_months": horizon,
        }
        if equity > ZERO:
            inv_payload["own_funds_year_month"] = first_ym
            inv_payload["own_funds_amount"] = str(equity)
        ops.append(
            BuildOp(
                op="add_entity",
                entity_type="investments",
                entity_id=inv_id,
                payload=inv_payload,
            )
        )

        benefit = d(inputs["benefit_amount"])
        monthly = benefit if inputs["benefit_cadence"] == "monthly" else benefit / D(12)

        if inputs["benefit_type"] == "revenue":
            rid = stable_id("rev", name, variant)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="revenue_streams",
                    entity_id=rid,
                    payload={
                        "id": rid,
                        "name": f"Benefit {name}",
                        "revenue_type": "recurring",
                        "start_year_month": first_ym,
                        "base_monthly_revenue": str(monthly),
                        "gross_margin_pct": str(d(inputs["gross_margin_pct"])),
                        "collection_days": 0,
                        "growth_annual": "0",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )
        else:
            cid = inputs.get("cost_item_id_to_reduce")
            current = None
            if cid:
                match = next((c for c in snapshot.cost_items if c.id == cid), None)
                if match and match.amount_monthly is not None:
                    current = match.amount_monthly
            sop, _ = savings_ops(
                opex_savings_monthly=monthly,
                cost_item_id_to_reduce=cid,
                current_amount=current,
                name_prefix=name,
                start_year_month=first_ym,
                variant=variant,
            )
            ops.extend(sop)

        meta = {
            "anchor_year_month": first_ym,
            "horizon_months": horizon,
            "discount_rate_annual": d(inputs["discount_rate_annual"]),
            "auto_finance_deficits": False,
            "open_year_month": first_ym,
        }
        return tuple(ops), meta
