"""Pack new_site — DECISION_PACKS §5."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper.build_ops import BuildOp
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot
from financetwin_engine.mapper.time import add_months
from financetwin_engine.packs.base import (
    BuiltScenarioBundle,
    Issue,
    PackInput,
    VariantPlan,
    has_errors,
)
from financetwin_engine.packs import defaults as R

ZERO = D(0)
PACK_ID = "new_site"

ACTUAL_KEYS = (
    "sales_monthly",
    "gross_margin_pct",
    "capex_total",
    "rent_monthly",
    "headcount",
    "payroll_monthly",
    "min_cash",
    "payback_months",
    "revenue_ramp_month_to_breakeven",
)


def _stable_id(kind: str, site_name: str, variant: str) -> str:
    """IDs deterministas: mismo input → mismos build_ops / hash."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(site_name).lower()).strip("-") or "site"
    return f"{kind}-{slug[:32]}-{variant}"


def _d(value: Any, default: Decimal | None = None) -> Decimal:
    if value is None:
        if default is not None:
            return default
        raise ValueError("missing money/rate value")
    if isinstance(value, float):
        raise TypeError("float not allowed in pack inputs")
    return D(value)


class NewSitePack:
    id = PACK_ID

    def inputs_schema(self) -> list[PackInput]:
        return [
            PackInput("site_name", "Nombre del establecimiento", "text", True),
            PackInput("open_year_month", "Mes de apertura", "year_month", True),
            PackInput("capex_total", "CAPEX total", "money", True),
            PackInput("sales_run_rate", "Ventas régimen €/mes", "money", True, default_resolver="avg_bu_revenue"),
            PackInput("gross_margin_pct", "Margen bruto", "rate", True, default_resolver="company_gross_margin"),
            PackInput("rent_monthly", "Alquiler mensual", "money", True),
            PackInput("sales_ramp_months", "Meses de rampa", "count", False),
            PackInput("collection_days", "Días de cobro", "count", False),
            PackInput("other_opex_monthly", "Otros opex fijos", "money", False),
            PackInput("other_opex_pct_sales", "Otros opex % ventas", "rate", False),
            PackInput("headcount", "Plantilla", "count", False),
            PackInput("employer_cost_per_person", "Coste empresa / persona", "money", False, default_resolver="avg_employer_cost"),
            PackInput("debt_amount", "Deuda", "money", False),
            PackInput("equity_amount", "Recursos propios", "money", False),
            PackInput("loan_term_months", "Plazo préstamo", "count", False),
            PackInput("loan_annual_rate", "TIN préstamo", "rate", False),
            PackInput("loan_grace_months", "Carencia (meses)", "count", False),
            PackInput("loan_grace_type", "Tipo carencia", "enum", False, enum_values=("capital", "total")),
            PackInput("loan_system", "Sistema amortización", "enum", False, enum_values=("french", "linear", "bullet")),
            PackInput("pre_open_months", "Meses pre-apertura", "count", False),
            PackInput("horizon_months", "Horizonte", "count", False),
            PackInput("discount_rate_annual", "Tasa descuento", "rate", False, default_resolver="debt_cost_plus_premium"),
        ]

    def actual_keys(self) -> list[str]:
        return list(ACTUAL_KEYS)

    def analysis_plan(self) -> dict[str, Any]:
        """Sensibilidad / inversa (§5.5). Ejecución completa de sweeps → F4+/analytics."""
        return {
            "sensitivity_vars": [
                "sales_run_rate",
                "gross_margin_pct",
                "capex_total",
                "rent_monthly",
                "loan_annual_rate",
            ],
            "inverse_sensitivity": [
                {"metric": "npv", "threshold": "0", "vs": ["sales_run_rate", "gross_margin_pct", "capex_total"]},
                {"metric": "min_cash", "threshold": "policy.min_cash", "vs": ["sales_run_rate"]},
            ],
            "stress_tests": [
                "sales_-15pct",
                "sales_-30pct",
                "open_plus_2m",
                "open_plus_4m",
                "rate_plus_200bp",
            ],
            "note": "MVP F3: metrics+policy via calculate(); sweeps not executed here",
        }

    def resolve_defaults(
        self,
        snapshot: CompanyTwinSnapshot,
        user_partial: dict[str, Any],
    ) -> dict[str, Any]:
        out = dict(user_partial)
        if "sales_run_rate" not in out:
            v = R.avg_bu_revenue(snapshot)
            if v is not None:
                out["sales_run_rate"] = v
        if "gross_margin_pct" not in out:
            v = R.company_gross_margin(snapshot)
            if v is not None:
                out["gross_margin_pct"] = v
        if "collection_days" not in out:
            out["collection_days"] = R.median_collection_days(snapshot)
        if "sales_ramp_months" not in out:
            out["sales_ramp_months"] = 12
        if "sales_ramp" not in out:
            out["sales_ramp"] = R.linear_ramp(int(out["sales_ramp_months"]))
        if "headcount" not in out:
            out["headcount"] = 0
        if "debt_amount" not in out:
            out["debt_amount"] = ZERO
        if "other_opex_monthly" not in out:
            out["other_opex_monthly"] = ZERO
        if "pre_open_months" not in out:
            out["pre_open_months"] = 0
        if "horizon_months" not in out:
            out["horizon_months"] = 84
        if "loan_term_months" not in out:
            out["loan_term_months"] = 84
        if "loan_grace_months" not in out:
            out["loan_grace_months"] = 0
        if "loan_system" not in out:
            out["loan_system"] = "french"
        if "discount_rate_annual" not in out:
            out["discount_rate_annual"] = R.debt_cost_plus_premium(snapshot)
        if "employer_cost_per_person" not in out and int(out.get("headcount") or 0) > 0:
            v = R.avg_employer_cost(snapshot)
            if v is not None:
                out["employer_cost_per_person"] = v
        # equity default after capex/debt known
        if "capex_total" in out and "equity_amount" not in out:
            debt = _d(out.get("debt_amount"), ZERO)
            out["equity_amount"] = max(ZERO, _d(out["capex_total"]) - debt)
        return out

    def validate_inputs(self, inputs: dict[str, Any]) -> list[Issue]:
        issues: list[Issue] = []
        required = ("site_name", "open_year_month", "capex_total", "sales_run_rate", "gross_margin_pct", "rent_monthly")
        for key in required:
            if key not in inputs or inputs[key] is None or inputs[key] == "":
                issues.append(Issue("error", "missing_required", f"missing required input: {key}"))

        if has_errors(issues):
            return issues

        capex = _d(inputs["capex_total"])
        debt = _d(inputs.get("debt_amount"), ZERO)
        equity = _d(inputs.get("equity_amount"), max(ZERO, capex - debt))
        funded = debt + equity
        if funded < capex:
            issues.append(
                Issue(
                    "error",
                    "funding_insufficient",
                    f"funded ({funded}) < capex_total ({capex}); pack does not auto_finance",
                )
            )
        elif funded > capex:
            issues.append(
                Issue(
                    "warning",
                    "funding_excess",
                    f"funded ({funded}) > capex_total ({capex}); excess remains as cash",
                )
            )

        headcount = int(inputs.get("headcount") or 0)
        if headcount < 0:
            issues.append(Issue("error", "invalid_headcount", "headcount must be >= 0"))
        if headcount > 0 and inputs.get("employer_cost_per_person") is None:
            issues.append(
                Issue("error", "missing_employer_cost", "employer_cost_per_person required when headcount>0")
            )

        if debt > ZERO:
            if inputs.get("loan_term_months") is None:
                issues.append(Issue("error", "missing_loan_term", "loan_term_months required when debt>0"))
            if inputs.get("loan_annual_rate") is None:
                issues.append(Issue("error", "missing_loan_rate", "loan_annual_rate required when debt>0"))
            grace = int(inputs.get("loan_grace_months") or 0)
            if grace > 0 and inputs.get("loan_grace_type") not in ("capital", "total"):
                issues.append(
                    Issue("error", "missing_grace_type", "loan_grace_type capital|total required when grace>0")
                )

        margin = _d(inputs["gross_margin_pct"])
        if margin < ZERO or margin > D(1):
            issues.append(Issue("error", "invalid_margin", "gross_margin_pct must be in [0,1]"))

        for money_key in ("capex_total", "sales_run_rate", "rent_monthly"):
            if _d(inputs[money_key]) < ZERO:
                issues.append(Issue("error", "negative_money", f"{money_key} must be >= 0"))

        return issues

    def build(
        self,
        snapshot: CompanyTwinSnapshot,
        inputs: dict[str, Any],
    ) -> BuiltScenarioBundle:
        resolved = self.resolve_defaults(snapshot, inputs)
        issues = self.validate_inputs(resolved)
        if has_errors(issues):
            msgs = "; ".join(i.message for i in issues if i.severity == "error")
            raise ValueError(f"new_site validate failed: {msgs}")

        base_ops, base_meta = self._build_ops(resolved, variant="base")
        cons_inputs = self._variant_inputs(resolved, "conservative")
        cons_ops, cons_meta = self._build_ops(cons_inputs, variant="conservative")
        adv_inputs = self._variant_inputs(resolved, "adverse")
        adv_ops, adv_meta = self._build_ops(adv_inputs, variant="adverse")

        return BuiltScenarioBundle(
            pack_id=PACK_ID,
            resolved_inputs=resolved,
            variants={
                "base": VariantPlan(
                    name="base",
                    build_ops=base_ops,
                    **base_meta,
                ),
                "conservative": VariantPlan(
                    name="conservative",
                    build_ops=cons_ops,
                    **cons_meta,
                ),
                "adverse": VariantPlan(
                    name="adverse",
                    build_ops=adv_ops,
                    **adv_meta,
                ),
            },
        )

    def _variant_inputs(self, base: dict[str, Any], variant: str) -> dict[str, Any]:
        inp = dict(base)
        sales = _d(base["sales_run_rate"])
        rent = _d(base["rent_monthly"])
        other = _d(base.get("other_opex_monthly"), ZERO)
        capex = _d(base["capex_total"])
        ramp = list(base.get("sales_ramp") or R.linear_ramp(int(base.get("sales_ramp_months") or 12)))

        if variant == "conservative":
            inp["sales_run_rate"] = sales * D("0.85")
            inp["rent_monthly"] = rent * D("1.05")
            inp["other_opex_monthly"] = other * D("1.05")
            if base.get("other_opex_pct_sales") is not None:
                inp["other_opex_pct_sales"] = _d(base["other_opex_pct_sales"]) * D("1.05")
            # ramp ×0.9 en primeros 6 meses
            new_ramp = []
            for i, f in enumerate(ramp):
                factor = D(f) if not isinstance(f, Decimal) else f
                if i < 6:
                    factor = factor * D("0.9")
                new_ramp.append(factor)
            inp["sales_ramp"] = tuple(new_ramp)
        elif variant == "adverse":
            inp["sales_run_rate"] = sales * D("0.70")
            inp["rent_monthly"] = rent * D("1.10")
            inp["other_opex_monthly"] = other * D("1.10")
            if base.get("other_opex_pct_sales") is not None:
                inp["other_opex_pct_sales"] = _d(base["other_opex_pct_sales"]) * D("1.10")
            inp["capex_total"] = capex * D("1.10")
            # open +2 months
            inp["open_year_month"] = add_months(str(base["open_year_month"]), 2)
            # Adjust equity default if was derived: keep debt, bump equity to cover new capex if needed
            debt = _d(base.get("debt_amount"), ZERO)
            new_capex = _d(inp["capex_total"])
            equity = _d(base.get("equity_amount"), ZERO)
            if debt + equity < new_capex:
                inp["equity_amount"] = new_capex - debt
        return inp

    def _build_ops(
        self,
        inputs: dict[str, Any],
        *,
        variant: str,
    ) -> tuple[tuple[BuildOp, ...], dict[str, Any]]:
        open_ym = str(inputs["open_year_month"])
        pre_open = int(inputs.get("pre_open_months") or 0)
        anchor = add_months(open_ym, -pre_open) if pre_open > 0 else open_ym
        horizon = int(inputs.get("horizon_months") or 84)
        discount = _d(inputs["discount_rate_annual"])

        site_name = str(inputs["site_name"])
        capex = _d(inputs["capex_total"])
        sales = _d(inputs["sales_run_rate"])
        margin = _d(inputs["gross_margin_pct"])
        rent = _d(inputs["rent_monthly"])
        other_fixed = _d(inputs.get("other_opex_monthly"), ZERO)
        other_pct = inputs.get("other_opex_pct_sales")
        headcount = int(inputs.get("headcount") or 0)
        collection_days = int(inputs.get("collection_days") or 30)
        ramp_months = int(inputs.get("sales_ramp_months") or 12)
        ramp = inputs.get("sales_ramp") or R.linear_ramp(ramp_months)
        ramp_list = [str(_d(x)) for x in ramp]

        debt = _d(inputs.get("debt_amount"), ZERO)
        equity = _d(inputs.get("equity_amount"), max(ZERO, capex - debt))

        bu_id = _stable_id("bu", site_name, variant)
        rev_id = _stable_id("rev", site_name, variant)
        rent_id = _stable_id("cost-rent", site_name, variant)
        inv_id = _stable_id("inv", site_name, variant)
        asset_id = _stable_id("asset", site_name, variant)
        loan_id = _stable_id("loan", site_name, variant) if debt > ZERO else None
        payroll_id = _stable_id("pay", site_name, variant) if headcount > 0 else None
        opex_fixed_id = (
            _stable_id("cost-opex", site_name, variant) if other_fixed > ZERO else None
        )
        opex_var_id = (
            _stable_id("cost-opex-var", site_name, variant)
            if other_pct is not None and _d(other_pct) > ZERO
            else None
        )

        ops: list[BuildOp] = []

        ops.append(
            BuildOp(
                op="add_entity",
                entity_type="business_units",
                entity_id=bu_id,
                payload={
                    "id": bu_id,
                    "name": site_name,
                    "unit_type": "store",
                    "start_year_month": open_ym,
                    "is_active": True,
                },
            )
        )
        ops.append(
            BuildOp(
                op="add_entity",
                entity_type="revenue_streams",
                entity_id=rev_id,
                payload={
                    "id": rev_id,
                    "name": f"Ventas {site_name}",
                    "revenue_type": "recurring",
                    "business_unit_id": bu_id,
                    "start_year_month": open_ym,
                    "base_monthly_revenue": str(sales),
                    "gross_margin_pct": str(margin),
                    "collection_days": collection_days,
                    "ramp": ramp_list,
                    "growth_annual": "0",
                    "origin": "user",
                    "confidence": "medium",
                },
            )
        )
        ops.append(
            BuildOp(
                op="add_entity",
                entity_type="cost_items",
                entity_id=rent_id,
                payload={
                    "id": rent_id,
                    "name": f"Alquiler {site_name}",
                    "nature": "fixed",
                    "business_unit_id": bu_id,
                    "start_year_month": open_ym,
                    "amount_monthly": str(rent),
                    "payment_days": 0,
                    "growth_annual": "0",
                    "origin": "user",
                    "confidence": "medium",
                },
            )
        )
        if opex_fixed_id:
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="cost_items",
                    entity_id=opex_fixed_id,
                    payload={
                        "id": opex_fixed_id,
                        "name": f"Opex {site_name}",
                        "nature": "fixed",
                        "business_unit_id": bu_id,
                        "start_year_month": open_ym,
                        "amount_monthly": str(other_fixed),
                        "payment_days": 0,
                        "growth_annual": "0",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )
        if opex_var_id:
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="cost_items",
                    entity_id=opex_var_id,
                    payload={
                        "id": opex_var_id,
                        "name": f"Opex var {site_name}",
                        "nature": "variable_pct_revenue",
                        "business_unit_id": bu_id,
                        "start_year_month": open_ym,
                        "pct_of_revenue": str(_d(other_pct)),
                        "payment_days": 0,
                        "growth_annual": "0",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )
        if payroll_id:
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="payroll",
                    entity_id=payroll_id,
                    payload={
                        "id": payroll_id,
                        "role_name": f"Staff {site_name}",
                        "headcount": headcount,
                        "monthly_employer_cost": str(_d(inputs["employer_cost_per_person"])),
                        "business_unit_id": bu_id,
                        "start_year_month": open_ym,
                        "payment_days": 0,
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )

        linked_rev = [rev_id]
        linked_cost = [rent_id]
        if opex_fixed_id:
            linked_cost.append(opex_fixed_id)
        if opex_var_id:
            linked_cost.append(opex_var_id)
        linked_pay = [payroll_id] if payroll_id else []
        linked_loan = [loan_id] if loan_id else []
        linked_asset = [asset_id]

        inv_payload: dict[str, Any] = {
            "id": inv_id,
            "name": f"Apertura {site_name}",
            "decision_pack_id": PACK_ID,
            "capex_schedule": [
                {
                    "year_month": open_ym,
                    "amount": str(capex),
                    "includes_vat": False,
                    "label": "capex_total",
                }
            ],
            "linked_revenue_stream_ids": linked_rev,
            "linked_cost_item_ids": linked_cost,
            "linked_payroll_ids": linked_pay,
            "linked_loan_ids": linked_loan,
            "linked_asset_ids": linked_asset,
            "analysis_start_year_month": open_ym,
            "analysis_horizon_months": horizon,
        }
        if equity > ZERO:
            inv_payload["own_funds_year_month"] = open_ym
            inv_payload["own_funds_amount"] = str(equity)

        ops.append(
            BuildOp(
                op="add_entity",
                entity_type="investments",
                entity_id=inv_id,
                payload=inv_payload,
            )
        )

        asset_funding = "loan" if loan_id else "cash"
        asset_payload: dict[str, Any] = {
            "id": asset_id,
            "name": f"Activo {site_name}",
            "acquisition_cost": str(capex),
            "acquisition_year_month": open_ym,
            "useful_life_months": max(horizon, 60),
            "residual_value": "0",
            "depreciation_method": "straight_line",
            "acquisition_funding": asset_funding,
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

        if loan_id:
            grace = int(inputs.get("loan_grace_months") or 0)
            grace_type = inputs.get("loan_grace_type") if grace > 0 else "none"
            ops.append(
                BuildOp(
                    op="add_entity",
                    entity_type="loans",
                    entity_id=loan_id,
                    payload={
                        "id": loan_id,
                        "name": f"Préstamo {site_name}",
                        "principal": str(debt),
                        "annual_interest_rate": str(_d(inputs["loan_annual_rate"])),
                        "term_months": int(inputs["loan_term_months"]),
                        "amortization_system": inputs.get("loan_system") or "french",
                        "grace_months": grace,
                        "grace_type": grace_type or "none",
                        "disbursement_year_month": open_ym,
                        "origination_fee": "0",
                        "rate_type": "fixed",
                        "origin": "user",
                        "confidence": "medium",
                    },
                )
            )

        meta = {
            "anchor_year_month": anchor,
            "horizon_months": horizon,
            "discount_rate_annual": discount,
            "auto_finance_deficits": False,
            "open_year_month": open_ym,
        }
        return tuple(ops), meta
