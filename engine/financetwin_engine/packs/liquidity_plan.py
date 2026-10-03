"""Pack liquidity_plan — DECISION_PACKS §10."""

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

PACK_ID = "liquidity_plan"


class LiquidityPlanPack:
    id = PACK_ID

    def inputs_schema(self) -> list[PackInput]:
        return [
            PackInput("horizon_months", "Horizonte", "count", True),
            PackInput("anchor_year_month", "Ancla", "year_month", True),
            PackInput("sales_adjustment_pct", "Ajuste ventas", "rate", False),
            PackInput("collection_days_delta", "Δ días cobro", "count", False),
            PackInput("payment_days_delta", "Δ días pago", "count", False),
            PackInput("extra_monthly_opex", "Opex extra", "money", False),
            PackInput("one_off_outflows", "Salidas puntuales", "json", False),
            PackInput("one_off_inflows", "Entradas puntuales", "json", False),
        ]

    def actual_keys(self) -> list[str]:
        return ["min_cash", "sales_monthly"]

    def resolve_defaults(self, snapshot: CompanyTwinSnapshot, user_partial: dict[str, Any]) -> dict[str, Any]:
        out = dict(user_partial)
        if "sales_adjustment_pct" not in out:
            out["sales_adjustment_pct"] = ZERO
        if "collection_days_delta" not in out:
            out["collection_days_delta"] = 0
        if "payment_days_delta" not in out:
            out["payment_days_delta"] = 0
        if "extra_monthly_opex" not in out:
            out["extra_monthly_opex"] = ZERO
        if "one_off_outflows" not in out:
            out["one_off_outflows"] = []
        if "one_off_inflows" not in out:
            out["one_off_inflows"] = []
        if "discount_rate_annual" not in out:
            out["discount_rate_annual"] = ZERO
        return out

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        if inputs.get("horizon_months") is None:
            issues.append(Issue("error", "missing_horizon", "horizon_months required"))
        if not inputs.get("anchor_year_month"):
            issues.append(Issue("error", "missing_anchor", "anchor_year_month required"))
        if has_errors(issues):
            return issues
        if int(inputs["horizon_months"]) < 1:
            issues.append(Issue("error", "bad_horizon", "horizon_months >= 1"))
        return issues

    def build(self, snapshot: CompanyTwinSnapshot, inputs: dict[str, Any]) -> BuiltScenarioBundle:
        resolved = self.resolve_defaults(snapshot, inputs)
        issues = self.validate_inputs(resolved)
        if has_errors(issues):
            raise ValueError("; ".join(i.message for i in issues if i.severity == "error"))

        variants: dict[str, VariantPlan] = {}
        # §10.5
        base_sales = d(resolved["sales_adjustment_pct"])
        base_coll = int(resolved["collection_days_delta"])
        specs = (
            ("base", base_sales, base_coll),
            ("conservative", base_sales - D("0.05"), base_coll),
            ("adverse", base_sales - D("0.15"), base_coll + 15),
        )
        for vname, sales_adj, coll_delta in specs:
            adj = dict(resolved)
            adj["sales_adjustment_pct"] = sales_adj
            adj["collection_days_delta"] = coll_delta
            ops, meta = self._ops(snapshot, adj, vname)
            variants[vname] = VariantPlan(name=vname, build_ops=ops, **meta)

        return BuiltScenarioBundle(pack_id=PACK_ID, variants=variants, resolved_inputs=resolved)

    def _ops(
        self,
        snapshot: CompanyTwinSnapshot,
        inputs: dict[str, Any],
        variant: str,
    ) -> tuple[tuple[BuildOp, ...], dict[str, Any]]:
        ops: list[BuildOp] = []
        sales_adj = d(inputs["sales_adjustment_pct"])
        coll_delta = int(inputs["collection_days_delta"])
        pay_delta = int(inputs["payment_days_delta"])

        for stream in snapshot.revenue_streams:
            new_rev = stream.base_monthly_revenue * (D(1) + sales_adj)
            if new_rev < ZERO:
                new_rev = ZERO
            ops.append(
                BuildOp(
                    op="set_field",
                    entity_type="revenue_streams",
                    entity_id=stream.id,
                    field="base_monthly_revenue",
                    value=str(new_rev),
                )
            )
            new_days = max(0, stream.collection_days + coll_delta)
            ops.append(
                BuildOp(
                    op="set_field",
                    entity_type="revenue_streams",
                    entity_id=stream.id,
                    field="collection_days",
                    value=new_days,
                )
            )

        for cost in snapshot.cost_items:
            new_days = max(0, cost.payment_days + pay_delta)
            ops.append(
                BuildOp(
                    op="set_field",
                    entity_type="cost_items",
                    entity_id=cost.id,
                    field="payment_days",
                    value=new_days,
                )
            )

        extra = d(inputs.get("extra_monthly_opex"), ZERO)
        if extra > ZERO:
            cid = stable_id("extra-opex", "liquidity", variant)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="cost_items",
                    entity_id=cid,
                    payload={
                        "id": cid,
                        "name": "Extra opex (liquidity plan)",
                        "nature": "fixed",
                        "start_year_month": str(inputs["anchor_year_month"]),
                        "amount_monthly": str(extra),
                        "payment_days": 0,
                        "growth_annual": "0",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )

        for i, ev in enumerate(inputs.get("one_off_outflows") or []):
            oid = stable_id(f"out-{i}", "liquidity", variant)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="one_off_cash_events",
                    entity_id=oid,
                    payload={
                        "id": oid,
                        "year_month": str(ev["year_month"]),
                        "amount": str(d(ev["amount"])),
                        "kind": "other_out",
                    },
                )
            )
        for i, ev in enumerate(inputs.get("one_off_inflows") or []):
            oid = stable_id(f"in-{i}", "liquidity", variant)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="one_off_cash_events",
                    entity_id=oid,
                    payload={
                        "id": oid,
                        "year_month": str(ev["year_month"]),
                        "amount": str(d(ev["amount"])),
                        "kind": "other_in",
                    },
                )
            )

        meta = {
            "anchor_year_month": str(inputs["anchor_year_month"]),
            "horizon_months": int(inputs["horizon_months"]),
            "discount_rate_annual": d(inputs.get("discount_rate_annual"), ZERO),
            "auto_finance_deficits": False,
            "open_year_month": str(inputs["anchor_year_month"]),
        }
        return tuple(ops), meta
