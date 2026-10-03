"""F4 — resto de packs MVP: build + calculate por pack."""

from financetwin_engine import (
    AssetPurchasePack,
    FinancingPack,
    GenericInvestmentPack,
    HiringPack,
    LiquidityPlanPack,
    run_variant,
    snapshot_from_dict,
)
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.invariants import check_invariants
from financetwin_engine.packs.base import has_errors

_CANONICAL = {
    "sales_monthly",
    "gross_margin_pct",
    "capex_total",
    "rent_monthly",
    "headcount",
    "payroll_monthly",
    "min_cash",
    "payback_months",
    "revenue_ramp_month_to_breakeven",
}


def _twin(**extra):
    data = {
        "schema_version": "1.0",
        "company": {"currency": "EUR", "opening_cash": "150000"},
        "fiscal": {
            "vat_rate": "0",
            "vat_settlement": "monthly",
            "vat_payment_lag_months": 0,
            "corp_tax_rate": "0",
            "corp_tax_payment_mode": "none",
        },
        "policies": {"min_cash": "0"},
        "revenue_streams": [
            {
                "id": "R0",
                "name": "base",
                "revenue_type": "recurring",
                "start_year_month": "2027-01",
                "base_monthly_revenue": "30000",
                "gross_margin_pct": "0.4",
                "collection_days": 0,
            }
        ],
        "cost_items": [
            {
                "id": "C0",
                "name": "opex",
                "nature": "fixed",
                "start_year_month": "2027-01",
                "amount_monthly": "5000",
                "payment_days": 0,
            }
        ],
    }
    data.update(extra)
    return snapshot_from_dict(data)


def _assert_pack_ok(pack, snap, inputs, variant="base"):
    assert set(pack.actual_keys()) <= _CANONICAL
    bundle = pack.build(snap, inputs)
    assert "base" in bundle.variants or variant in bundle.variants
    plan = bundle.variants.get(variant) or bundle.variants["base"]
    assert plan.auto_finance_deficits is False
    # snapshot not mutated
    n_rev = len(snap.revenue_streams)
    pr = run_variant(snap, plan)
    assert len(snap.revenue_streams) == n_rev
    assert pr.result.financing_need is not None
    check_invariants(pr.result, assets=pr.mapped.calculation_input.assets)
    return bundle, pr


def test_financing_cash_buffer() -> None:
    pack = FinancingPack()
    snap = _twin()
    bundle, pr = _assert_pack_ok(
        pack,
        snap,
        {
            "loan_name": "Puente",
            "principal": "50000",
            "disbursement_year_month": "2027-01",
            "annual_rate": "0.06",
            "term_months": 24,
            "use_of_funds": "cash_buffer",
            "horizon_months": 24,
        },
    )
    assert set(bundle.variants) == {"base", "conservative", "adverse"}
    assert pr.result.cash_flow[0].loan_drawdowns == D(50000)
    # rate variants differ
    assert (
        bundle.variants["adverse"].build_ops[0].payload["annual_interest_rate"]
        != bundle.variants["base"].build_ops[0].payload["annual_interest_rate"]
    )


def test_financing_capex_use() -> None:
    pack = FinancingPack()
    snap = _twin()
    _, pr = _assert_pack_ok(
        pack,
        snap,
        {
            "loan_name": "CapexLoan",
            "principal": "80000",
            "disbursement_year_month": "2027-01",
            "annual_rate": "0.05",
            "term_months": 36,
            "use_of_funds": "capex",
            "linked_capex": "80000",
            "horizon_months": 24,
        },
    )
    assert pr.result.cash_flow[0].capex_paid == D(80000)
    assert pr.result.cash_flow[0].loan_drawdowns == D(80000)


def test_financing_grace_missing_type_error() -> None:
    pack = FinancingPack()
    issues = pack.validate_inputs(
        pack.resolve_defaults(
            _twin(),
            {
                "loan_name": "X",
                "principal": "10000",
                "disbursement_year_month": "2027-01",
                "annual_rate": "0.05",
                "term_months": 12,
                "grace_months": 3,
                "use_of_funds": "general",
            },
        )
    )
    assert has_errors(issues)


def test_asset_purchase_cash() -> None:
    pack = AssetPurchasePack()
    snap = _twin()
    _, pr = _assert_pack_ok(
        pack,
        snap,
        {
            "asset_name": "Furgoneta",
            "acquisition_cost": "25000",
            "acquisition_year_month": "2027-01",
            "useful_life_months": 60,
            "funding_mode": "cash",
            "opex_savings_monthly": "400",
            "horizon_months": 24,
            "discount_rate_annual": "0.08",
        },
    )
    assert pr.result.cash_flow[0].capex_paid == D(25000)


def test_asset_purchase_leasing_no_capex() -> None:
    pack = AssetPurchasePack()
    snap = _twin()
    bundle, pr = _assert_pack_ok(
        pack,
        snap,
        {
            "asset_name": "Copier",
            "acquisition_cost": "10000",  # ignored for leasing cash path
            "acquisition_year_month": "2027-01",
            "useful_life_months": 36,
            "funding_mode": "leasing_as_cost",
            "leasing_monthly": "300",
            "leasing_term_months": 36,
            "horizon_months": 24,
            "discount_rate_annual": "0.08",
        },
    )
    assert pr.result.cash_flow[0].capex_paid == D(0)
    # leasing cost present
    assert any(
        c.amount_monthly == D(300)
        for c in pr.mapped.effective_snapshot.cost_items
        if c.amount_monthly is not None
    )
    issues = pack.validate_inputs(bundle.resolved_inputs)
    assert any(i.code == "leasing_simplification" for i in issues)


def test_asset_savings_no_negative_cost() -> None:
    pack = AssetPurchasePack()
    snap = _twin()
    bundle = pack.build(
        snap,
        {
            "asset_name": "Machine",
            "acquisition_cost": "10000",
            "acquisition_year_month": "2027-01",
            "useful_life_months": 60,
            "funding_mode": "cash",
            "opex_savings_monthly": "800",
            "cost_item_id_to_reduce": "C0",
            "horizon_months": 12,
            "discount_rate_annual": "0.08",
        },
    )
    pr = run_variant(snap, bundle.variants["base"])
    c0 = next(c for c in pr.mapped.effective_snapshot.cost_items if c.id == "C0")
    assert c0.amount_monthly == D(4200)  # 5000-800
    assert c0.amount_monthly >= D(0)


def test_hiring_with_uplift() -> None:
    pack = HiringPack()
    snap = _twin()
    bundle, pr = _assert_pack_ok(
        pack,
        snap,
        {
            "role_name": "Comercial",
            "headcount": 2,
            "employer_cost_per_person": "3000",
            "start_year_month": "2027-01",
            "expected_monthly_revenue_uplift": "8000",
            "gross_margin_pct": "0.4",
            "horizon_months": 12,
            "discount_rate_annual": "0.08",
        },
    )
    assert set(bundle.variants) == {"base", "conservative", "adverse"}
    # adverse: uplift 0
    adv = run_variant(snap, bundle.variants["adverse"])
    assert all(
        not s.id.startswith("rev-")
        for s in adv.mapped.calculation_input.revenue_streams
        if "Comercial" in (s.name or "")
    ) or len([s for s in adv.mapped.calculation_input.revenue_streams if "Uplift" in s.name]) == 0


def test_generic_investment_revenue_benefit() -> None:
    pack = GenericInvestmentPack()
    snap = _twin()
    _, pr = _assert_pack_ok(
        pack,
        snap,
        {
            "name": "Software",
            "capex_schedule": [{"year_month": "2027-01", "amount": "20000"}],
            "horizon_months": 24,
            "benefit_cadence": "monthly",
            "benefit_amount": "1500",
            "benefit_type": "revenue",
            "gross_margin_pct": "0.8",
            "debt_amount": "0",
            "equity_amount": "20000",
            "discount_rate_annual": "0.08",
        },
    )
    assert pr.result.investment_metrics is not None
    assert pr.result.cash_flow[0].capex_paid == D(20000)


def test_generic_investment_opex_reduction_stream() -> None:
    pack = GenericInvestmentPack()
    snap = _twin()
    bundle = pack.build(
        snap,
        {
            "name": "Efficiency",
            "capex_schedule": [{"year_month": "2027-01", "amount": "5000"}],
            "horizon_months": 12,
            "benefit_cadence": "monthly",
            "benefit_amount": "400",
            "benefit_type": "opex_reduction",
            "equity_amount": "5000",
            "discount_rate_annual": "0.08",
        },
    )
    pr = run_variant(snap, bundle.variants["base"])
    assert any(
        "Ahorro opex" in (s.name or "")
        for s in pr.mapped.effective_snapshot.revenue_streams
    )


def test_liquidity_plan_adjusts_sales() -> None:
    pack = LiquidityPlanPack()
    snap = _twin()
    bundle, pr = _assert_pack_ok(
        pack,
        snap,
        {
            "horizon_months": 12,
            "anchor_year_month": "2027-01",
            "sales_adjustment_pct": "-0.10",
            "extra_monthly_opex": "1000",
            "one_off_outflows": [{"year_month": "2027-03", "amount": "5000", "label": "tax"}],
        },
    )
    assert set(bundle.variants) == {"base", "conservative", "adverse"}
    # base sales * 0.9
    r0 = next(s for s in pr.mapped.effective_snapshot.revenue_streams if s.id == "R0")
    assert r0.base_monthly_revenue == D(30000) * D("0.9")
    assert pr.result.cash_flow[2].operating_cash_flow != pr.result.cash_flow[0].operating_cash_flow
