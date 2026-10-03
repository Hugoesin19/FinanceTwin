"""Pack financing — DECISION_PACKS §6."""

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

PACK_ID = "financing"


class FinancingPack:
    id = PACK_ID

    def inputs_schema(self) -> list[PackInput]:
        return [
            PackInput("loan_name", "Nombre", "text", True),
            PackInput("principal", "Principal", "money", True),
            PackInput("disbursement_year_month", "Mes disposición", "year_month", True),
            PackInput("annual_rate", "TIN anual", "rate", True),
            PackInput("term_months", "Plazo (meses)", "count", True),
            PackInput("system", "Sistema", "enum", False, enum_values=("french", "linear", "bullet")),
            PackInput("grace_months", "Carencia", "count", False),
            PackInput("grace_type", "Tipo carencia", "enum", False, enum_values=("capital", "total")),
            PackInput("origination_fee", "Comisión apertura", "money", False),
            PackInput(
                "use_of_funds",
                "Uso de fondos",
                "enum",
                True,
                enum_values=("cash_buffer", "capex", "refinance_placeholder", "general"),
            ),
            PackInput("linked_capex", "CAPEX ligado", "money", False),
            PackInput("horizon_months", "Horizonte", "count", False),
            PackInput("discount_rate_annual", "Tasa descuento", "rate", False),
        ]

    def actual_keys(self) -> list[str]:
        # §6.6: min_cash + capex_total si use=capex (devolver unión ⊆ catálogo)
        return ["min_cash", "capex_total"]

    def resolve_defaults(self, snapshot: CompanyTwinSnapshot, user_partial: dict[str, Any]) -> dict[str, Any]:
        out = dict(user_partial)
        if "loan_name" not in out:
            out["loan_name"] = f"Préstamo {out.get('disbursement_year_month', '')}".strip()
        if "system" not in out:
            out["system"] = "french"
        if "grace_months" not in out:
            out["grace_months"] = 0
        if "origination_fee" not in out:
            out["origination_fee"] = ZERO
        if "horizon_months" not in out:
            out["horizon_months"] = 36
        if "discount_rate_annual" not in out and "annual_rate" in out:
            out["discount_rate_annual"] = out["annual_rate"]
        elif "discount_rate_annual" not in out:
            out["discount_rate_annual"] = R.debt_cost_plus_premium(snapshot)
        return out

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        for key in ("loan_name", "principal", "disbursement_year_month", "annual_rate", "term_months", "use_of_funds"):
            if key not in inputs or inputs[key] in (None, ""):
                issues.append(Issue("error", "missing_required", f"missing: {key}"))
        if has_errors(issues):
            return issues
        grace = int(inputs.get("grace_months") or 0)
        if grace > 0 and inputs.get("grace_type") not in ("capital", "total"):
            issues.append(Issue("error", "missing_grace_type", "grace_type required when grace>0"))
        use = inputs["use_of_funds"]
        if use not in ("cash_buffer", "capex", "refinance_placeholder", "general"):
            issues.append(Issue("error", "invalid_use", f"invalid use_of_funds: {use}"))
        if use == "capex":
            if inputs.get("linked_capex") is None or d(inputs["linked_capex"]) <= ZERO:
                issues.append(Issue("error", "missing_capex", "linked_capex > 0 required when use=capex"))
        if use == "refinance_placeholder":
            issues.append(
                Issue(
                    "warning",
                    "refinance_placeholder",
                    "refinance_placeholder does not cancel existing loans in MVP",
                )
            )
        if d(inputs["principal"]) <= ZERO:
            issues.append(Issue("error", "invalid_principal", "principal must be > 0"))
        return issues

    def build(self, snapshot: CompanyTwinSnapshot, inputs: dict[str, Any]) -> BuiltScenarioBundle:
        resolved = self.resolve_defaults(snapshot, inputs)
        issues = self.validate_inputs(resolved)
        if has_errors(issues):
            raise ValueError("; ".join(i.message for i in issues if i.severity == "error"))

        variants: dict[str, VariantPlan] = {}
        # base; conservative rate+100bp; adverse rate+300bp (§6.3)
        for name, bp in (("base", "0"), ("conservative", "0.01"), ("adverse", "0.03")):
            adj = dict(resolved)
            adj["annual_rate"] = d(resolved["annual_rate"]) + D(bp)
            ops, meta = self._ops(adj, name)
            variants[name] = VariantPlan(name=name, build_ops=ops, **meta)

        return BuiltScenarioBundle(pack_id=PACK_ID, variants=variants, resolved_inputs=resolved)

    def _ops(self, inputs: dict[str, Any], variant: str) -> tuple[tuple[BuildOp, ...], dict[str, Any]]:
        name = str(inputs["loan_name"])
        ym = str(inputs["disbursement_year_month"])
        principal = d(inputs["principal"])
        loan_id = stable_id("loan", name, variant)
        grace = int(inputs.get("grace_months") or 0)
        ops: list[BuildOp] = [
            BuildOp(
                op="add_entity",
                entity_type="loans",
                entity_id=loan_id,
                payload={
                    "id": loan_id,
                    "name": name,
                    "principal": str(principal),
                    "annual_interest_rate": str(d(inputs["annual_rate"])),
                    "term_months": int(inputs["term_months"]),
                    "amortization_system": inputs.get("system") or "french",
                    "grace_months": grace,
                    "grace_type": (inputs.get("grace_type") if grace > 0 else "none"),
                    "disbursement_year_month": ym,
                    "origination_fee": str(d(inputs.get("origination_fee"), ZERO)),
                    "rate_type": "fixed",
                    "origin": "user",
                    "confidence": "medium",
                },
            )
        ]
        use = inputs["use_of_funds"]
        if use == "capex":
            capex = d(inputs["linked_capex"])
            inv_id = stable_id("inv", name, variant)
            asset_id = stable_id("asset", name, variant)
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="investments",
                    entity_id=inv_id,
                    payload={
                        "id": inv_id,
                        "name": f"CAPEX {name}",
                        "decision_pack_id": PACK_ID,
                        "capex_schedule": [
                            {"year_month": ym, "amount": str(capex), "includes_vat": False}
                        ],
                        "linked_loan_ids": [loan_id],
                        "linked_asset_ids": [asset_id],
                        "analysis_start_year_month": ym,
                        "analysis_horizon_months": int(inputs["horizon_months"]),
                    },
                )
            )
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="assets",
                    entity_id=asset_id,
                    payload={
                        "id": asset_id,
                        "name": f"Activo {name}",
                        "acquisition_cost": str(capex),
                        "acquisition_year_month": ym,
                        "useful_life_months": max(int(inputs["horizon_months"]), 60),
                        "residual_value": "0",
                        "depreciation_method": "straight_line",
                        "acquisition_funding": "loan",
                        "funding_loan_id": loan_id,
                        "investment_id": inv_id,
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )
        meta = {
            "anchor_year_month": ym,
            "horizon_months": int(inputs["horizon_months"]),
            "discount_rate_annual": d(inputs["discount_rate_annual"]),
            "auto_finance_deficits": False,
            "open_year_month": ym,
        }
        return tuple(ops), meta
