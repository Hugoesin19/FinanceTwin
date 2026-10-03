"""Pack hiring — DECISION_PACKS §8."""

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
from financetwin_engine.packs.common import ZERO, d, stable_id
from financetwin_engine.packs import defaults as R

PACK_ID = "hiring"


class HiringPack:
    id = PACK_ID

    def inputs_schema(self) -> list[PackInput]:
        return [
            PackInput("role_name", "Rol", "text", True),
            PackInput("headcount", "Headcount", "count", True),
            PackInput("employer_cost_per_person", "Coste empresa", "money", True),
            PackInput("start_year_month", "Inicio", "year_month", True),
            PackInput("end_year_month", "Fin", "year_month", False),
            PackInput("expected_monthly_revenue_uplift", "Uplift ventas", "money", False),
            PackInput("gross_margin_pct", "Margen", "rate", False),
            PackInput("horizon_months", "Horizonte", "count", False),
            PackInput("discount_rate_annual", "Tasa descuento", "rate", False),
        ]

    def actual_keys(self) -> list[str]:
        return ["headcount", "payroll_monthly", "sales_monthly", "min_cash"]

    def resolve_defaults(self, snapshot: CompanyTwinSnapshot, user_partial: dict[str, Any]) -> dict[str, Any]:
        out = dict(user_partial)
        if "employer_cost_per_person" not in out:
            v = R.avg_employer_cost(snapshot)
            if v is not None:
                out["employer_cost_per_person"] = v
        if "expected_monthly_revenue_uplift" not in out:
            out["expected_monthly_revenue_uplift"] = ZERO
        if "horizon_months" not in out:
            out["horizon_months"] = 24
        if "discount_rate_annual" not in out:
            out["discount_rate_annual"] = R.debt_cost_plus_premium(snapshot)
        if d(out.get("expected_monthly_revenue_uplift"), ZERO) > ZERO and "gross_margin_pct" not in out:
            v = R.company_gross_margin(snapshot)
            if v is not None:
                out["gross_margin_pct"] = v
        if "uplift_ramp" not in out:
            out["uplift_ramp"] = R.linear_ramp(6)
        return out

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        for key in ("role_name", "headcount", "employer_cost_per_person", "start_year_month"):
            if key not in inputs or inputs[key] in (None, ""):
                issues.append(Issue("error", "missing_required", f"missing: {key}"))
        if has_errors(issues):
            return issues
        if int(inputs["headcount"]) < 1:
            issues.append(Issue("error", "invalid_headcount", "headcount must be >= 1"))
        uplift = d(inputs.get("expected_monthly_revenue_uplift"), ZERO)
        if uplift > ZERO and inputs.get("gross_margin_pct") is None:
            issues.append(Issue("error", "missing_margin", "gross_margin_pct required when uplift>0"))
        return issues

    def build(self, snapshot: CompanyTwinSnapshot, inputs: dict[str, Any]) -> BuiltScenarioBundle:
        resolved = self.resolve_defaults(snapshot, inputs)
        issues = self.validate_inputs(resolved)
        if has_errors(issues):
            raise ValueError("; ".join(i.message for i in issues if i.severity == "error"))

        variants: dict[str, VariantPlan] = {}
        # §8.2 conservative uplift×0.7; adverse uplift=0 cost×1.0
        specs = (
            ("base", D(1), D(1)),
            ("conservative", D("0.7"), D(1)),
            ("adverse", D(0), D(1)),
        )
        for vname, uplift_f, _cost_f in specs:
            adj = dict(resolved)
            adj["expected_monthly_revenue_uplift"] = (
                d(resolved.get("expected_monthly_revenue_uplift"), ZERO) * uplift_f
            )
            ops, meta = self._ops(adj, vname)
            variants[vname] = VariantPlan(name=vname, build_ops=ops, **meta)

        return BuiltScenarioBundle(pack_id=PACK_ID, variants=variants, resolved_inputs=resolved)

    def _ops(self, inputs: dict[str, Any], variant: str) -> tuple[tuple[BuildOp, ...], dict[str, Any]]:
        role = str(inputs["role_name"])
        start = str(inputs["start_year_month"])
        pay_id = stable_id("pay", role, variant)
        ops: list[BuildOp] = [
            BuildOp(
                op="add_entity",
                entity_type="payroll",
                entity_id=pay_id,
                payload={
                    "id": pay_id,
                    "role_name": role,
                    "headcount": int(inputs["headcount"]),
                    "monthly_employer_cost": str(d(inputs["employer_cost_per_person"])),
                    "start_year_month": start,
                    "end_year_month": inputs.get("end_year_month"),
                    "payment_days": 0,
                    "origin": "user",
                    "confidence": "medium",
                },
            )
        ]
        uplift = d(inputs.get("expected_monthly_revenue_uplift"), ZERO)
        if uplift > ZERO:
            rid = stable_id("rev", role, variant)
            ramp = inputs.get("uplift_ramp") or R.linear_ramp(6)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="revenue_streams",
                    entity_id=rid,
                    payload={
                        "id": rid,
                        "name": f"Uplift {role}",
                        "revenue_type": "recurring",
                        "start_year_month": start,
                        "end_year_month": inputs.get("end_year_month"),
                        "base_monthly_revenue": str(uplift),
                        "gross_margin_pct": str(d(inputs["gross_margin_pct"])),
                        "collection_days": 0,
                        "ramp": [str(d(x)) for x in ramp],
                        "growth_annual": "0",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )
        meta = {
            "anchor_year_month": start,
            "horizon_months": int(inputs["horizon_months"]),
            "discount_rate_annual": d(inputs["discount_rate_annual"]),
            "auto_finance_deficits": False,
            "open_year_month": start,
        }
        return tuple(ops), meta
