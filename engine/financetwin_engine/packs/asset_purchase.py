"""Pack asset_purchase — DECISION_PACKS §7."""

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

PACK_ID = "asset_purchase"


class AssetPurchasePack:
    id = PACK_ID

    def inputs_schema(self) -> list[PackInput]:
        return [
            PackInput("asset_name", "Activo", "text", True),
            PackInput("acquisition_cost", "Coste adquisición", "money", True),
            PackInput("acquisition_year_month", "Mes adquisición", "year_month", True),
            PackInput("useful_life_months", "Vida útil (meses)", "count", True),
            PackInput("funding_mode", "Financiación", "enum", True, enum_values=("cash", "loan", "leasing_as_cost")),
            PackInput("residual_value", "Valor residual", "money", False),
            PackInput("depreciation_method", "Amortización", "enum", False, enum_values=("straight_line", "declining_simple")),
            PackInput("loan_principal", "Principal préstamo", "money", False),
            PackInput("loan_annual_rate", "TIN", "rate", False),
            PackInput("loan_term_months", "Plazo préstamo", "count", False),
            PackInput("loan_grace_months", "Carencia", "count", False),
            PackInput("loan_grace_type", "Tipo carencia", "enum", False, enum_values=("capital", "total")),
            PackInput("leasing_monthly", "Cuota leasing", "money", False),
            PackInput("leasing_term_months", "Plazo leasing", "count", False),
            PackInput("opex_savings_monthly", "Ahorro opex/mes", "money", False),
            PackInput("cost_item_id_to_reduce", "Coste a reducir", "text", False),
            PackInput("revenue_uplift_monthly", "Uplift ventas/mes", "money", False),
            PackInput("gross_margin_pct", "Margen uplift", "rate", False),
            PackInput("horizon_months", "Horizonte", "count", False),
            PackInput("discount_rate_annual", "Tasa descuento", "rate", False),
            PackInput("compare_funding_modes", "Comparar modos", "bool", False),
        ]

    def actual_keys(self) -> list[str]:
        return ["capex_total", "min_cash", "sales_monthly", "payback_months"]

    def resolve_defaults(self, snapshot: CompanyTwinSnapshot, user_partial: dict[str, Any]) -> dict[str, Any]:
        out = dict(user_partial)
        if "residual_value" not in out:
            out["residual_value"] = ZERO
        if "depreciation_method" not in out:
            out["depreciation_method"] = "straight_line"
        if "opex_savings_monthly" not in out:
            out["opex_savings_monthly"] = ZERO
        if "revenue_uplift_monthly" not in out:
            out["revenue_uplift_monthly"] = ZERO
        if "loan_grace_months" not in out:
            out["loan_grace_months"] = 0
        if "compare_funding_modes" not in out:
            out["compare_funding_modes"] = False
        if "horizon_months" not in out:
            life = int(out.get("useful_life_months") or 60)
            lease = int(out.get("leasing_term_months") or 0)
            out["horizon_months"] = max(life, lease, 60)
        if "discount_rate_annual" not in out:
            out["discount_rate_annual"] = R.debt_cost_plus_premium(snapshot)
        if out.get("funding_mode") == "loan" and "loan_principal" not in out and "acquisition_cost" in out:
            out["loan_principal"] = out["acquisition_cost"]
        return out

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        for key in ("asset_name", "acquisition_cost", "acquisition_year_month", "useful_life_months", "funding_mode"):
            if key not in inputs or inputs[key] in (None, ""):
                issues.append(Issue("error", "missing_required", f"missing: {key}"))
        if has_errors(issues):
            return issues
        mode = inputs["funding_mode"]
        if mode not in ("cash", "loan", "leasing_as_cost"):
            issues.append(Issue("error", "invalid_mode", f"bad funding_mode: {mode}"))
        if mode == "loan":
            for k in ("loan_principal", "loan_annual_rate", "loan_term_months"):
                if inputs.get(k) is None:
                    issues.append(Issue("error", "missing_loan", f"{k} required for loan"))
            grace = int(inputs.get("loan_grace_months") or 0)
            if grace > 0 and inputs.get("loan_grace_type") not in ("capital", "total"):
                issues.append(Issue("error", "missing_grace_type", "grace_type required"))
        if mode == "leasing_as_cost":
            if inputs.get("leasing_monthly") is None or inputs.get("leasing_term_months") is None:
                issues.append(Issue("error", "missing_leasing", "leasing_monthly and term required"))
            issues.append(
                Issue(
                    "warning",
                    "leasing_simplification",
                    "leasing_as_cost is a cash simplification; not full lease accounting; purchase VAN/TIR not applied",
                )
            )
        uplift = d(inputs.get("revenue_uplift_monthly"), ZERO)
        if uplift > ZERO and inputs.get("gross_margin_pct") is None:
            issues.append(Issue("error", "missing_margin", "gross_margin_pct required when uplift>0"))
        return issues

    def build(self, snapshot: CompanyTwinSnapshot, inputs: dict[str, Any]) -> BuiltScenarioBundle:
        resolved = self.resolve_defaults(snapshot, inputs)
        issues = self.validate_inputs(resolved)
        # warnings allowed
        if has_errors(issues):
            raise ValueError("; ".join(i.message for i in issues if i.severity == "error"))

        variants: dict[str, VariantPlan] = {}
        modes = [resolved["funding_mode"]]
        if resolved.get("compare_funding_modes"):
            modes = []
            # omit modes missing inputs
            modes.append("cash")
            if resolved.get("loan_annual_rate") is not None and resolved.get("loan_term_months") is not None:
                modes.append("loan")
            if resolved.get("leasing_monthly") is not None and resolved.get("leasing_term_months") is not None:
                modes.append("leasing_as_cost")

        if resolved.get("compare_funding_modes"):
            for mode in modes:
                adj = dict(resolved)
                adj["funding_mode"] = mode
                if mode == "loan" and adj.get("loan_principal") is None:
                    adj["loan_principal"] = adj["acquisition_cost"]
                # validate skip for compare siblings if incomplete
                if mode == "loan" and adj.get("loan_annual_rate") is None:
                    continue
                if mode == "leasing_as_cost" and adj.get("leasing_monthly") is None:
                    continue
                ops, meta = self._ops(snapshot, adj, mode)
                variants[mode] = VariantPlan(name=mode, build_ops=ops, **meta)
        else:
            # base + conservative/adverse on savings/uplift (+ coste leasing / CAPEX §3.1)
            for vname, sales_f, cost_f in (
                ("base", "1", "1"),
                ("conservative", "0.85", "1.05"),
                ("adverse", "0.70", "1.10"),
            ):
                adj = dict(resolved)
                adj["revenue_uplift_monthly"] = d(resolved.get("revenue_uplift_monthly"), ZERO) * D(sales_f)
                adj["opex_savings_monthly"] = d(resolved.get("opex_savings_monthly"), ZERO) * D(sales_f)
                mode = resolved["funding_mode"]
                if mode == "leasing_as_cost":
                    adj["leasing_monthly"] = d(resolved["leasing_monthly"]) * D(cost_f)
                elif mode in ("cash", "loan"):
                    adj["acquisition_cost"] = d(resolved["acquisition_cost"]) * D(cost_f)
                    if mode == "loan":
                        adj["loan_principal"] = d(
                            resolved.get("loan_principal"), resolved["acquisition_cost"]
                        ) * D(cost_f)
                ops, meta = self._ops(snapshot, adj, vname)
                variants[vname] = VariantPlan(name=vname, build_ops=ops, **meta)

        return BuiltScenarioBundle(
            pack_id=PACK_ID,
            variants=variants,
            resolved_inputs=resolved,
        )

    def _ops(
        self,
        snapshot: CompanyTwinSnapshot,
        inputs: dict[str, Any],
        variant: str,
    ) -> tuple[tuple[BuildOp, ...], dict[str, Any]]:
        name = str(inputs["asset_name"])
        ym = str(inputs["acquisition_year_month"])
        mode = inputs["funding_mode"]
        cost = d(inputs["acquisition_cost"])
        horizon = int(inputs["horizon_months"])
        ops: list[BuildOp] = []

        if mode == "leasing_as_cost":
            lease_id = stable_id("lease", name, variant)
            term = int(inputs["leasing_term_months"])
            end_ym = None
            # end inclusive: start + term - 1 months — mapper uses end_year_month
            from financetwin_engine.mapper.time import add_months

            end_ym = add_months(ym, term - 1)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="cost_items",
                    entity_id=lease_id,
                    payload={
                        "id": lease_id,
                        "name": f"Leasing {name}",
                        "nature": "fixed",
                        "start_year_month": ym,
                        "end_year_month": end_ym,
                        "amount_monthly": str(d(inputs["leasing_monthly"])),
                        "payment_days": 0,
                        "growth_annual": "0",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )
        else:
            inv_id = stable_id("inv", name, variant)
            asset_id = stable_id("asset", name, variant)
            loan_id = None
            linked_loans: list[str] = []
            if mode == "loan":
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
                            "principal": str(d(inputs["loan_principal"])),
                            "annual_interest_rate": str(d(inputs["loan_annual_rate"])),
                            "term_months": int(inputs["loan_term_months"]),
                            "amortization_system": "french",
                            "grace_months": grace,
                            "grace_type": (inputs.get("loan_grace_type") if grace > 0 else "none"),
                            "disbursement_year_month": ym,
                            "origination_fee": "0",
                            "rate_type": "fixed",
                            "origin": "user",
                            "confidence": "medium",
                        },
                    )
                )
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="investments",
                    entity_id=inv_id,
                    payload={
                        "id": inv_id,
                        "name": f"Compra {name}",
                        "decision_pack_id": PACK_ID,
                        "capex_schedule": [
                            {"year_month": ym, "amount": str(cost), "includes_vat": False}
                        ],
                        "linked_loan_ids": linked_loans,
                        "linked_asset_ids": [asset_id],
                        "analysis_start_year_month": ym,
                        "analysis_horizon_months": horizon,
                    },
                )
            )
            asset_payload: dict[str, Any] = {
                "id": asset_id,
                "name": name,
                "acquisition_cost": str(cost),
                "acquisition_year_month": ym,
                "useful_life_months": int(inputs["useful_life_months"]),
                "residual_value": str(d(inputs.get("residual_value"), ZERO)),
                "depreciation_method": inputs.get("depreciation_method") or "straight_line",
                "acquisition_funding": "loan" if loan_id else "cash",
                "investment_id": inv_id,
                "origin": "user",
                "confidence": "medium",
            }
            if loan_id:
                asset_payload["funding_loan_id"] = loan_id
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="assets",
                    entity_id=asset_id,
                    payload=asset_payload,
                )
            )

        # uplift
        uplift = d(inputs.get("revenue_uplift_monthly"), ZERO)
        if uplift > ZERO:
            rid = stable_id("rev-uplift", name, variant)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="revenue_streams",
                    entity_id=rid,
                    payload={
                        "id": rid,
                        "name": f"Uplift {name}",
                        "revenue_type": "recurring",
                        "start_year_month": ym,
                        "base_monthly_revenue": str(uplift),
                        "gross_margin_pct": str(d(inputs["gross_margin_pct"])),
                        "collection_days": 0,
                        "growth_annual": "0",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )

        # savings §2.5
        savings = d(inputs.get("opex_savings_monthly"), ZERO)
        cid = inputs.get("cost_item_id_to_reduce")
        current = None
        if cid:
            match = next((c for c in snapshot.cost_items if c.id == cid), None)
            if match and match.amount_monthly is not None:
                current = match.amount_monthly
        sop, _ = savings_ops(
            opex_savings_monthly=savings,
            cost_item_id_to_reduce=cid,
            current_amount=current,
            name_prefix=name,
            start_year_month=ym,
            variant=variant,
        )
        ops.extend(sop)

        meta = {
            "anchor_year_month": ym,
            "horizon_months": horizon,
            "discount_rate_annual": d(inputs["discount_rate_annual"]),
            "auto_finance_deficits": False,
            "open_year_month": ym,
        }
        return tuple(ops), meta
