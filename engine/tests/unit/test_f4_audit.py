"""Auditoría F4 — huecos packs restantes."""

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
from financetwin_engine.packs.base import has_errors


def _twin():
    return snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {"currency": "EUR", "opening_cash": "200000"},
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
                    "base_monthly_revenue": "20000",
                    "gross_margin_pct": "0.4",
                    "collection_days": 30,
                }
            ],
            "cost_items": [
                {
                    "id": "C0",
                    "name": "opex",
                    "nature": "fixed",
                    "start_year_month": "2027-01",
                    "amount_monthly": "4000",
                    "payment_days": 30,
                }
            ],
        }
    )


def test_financing_refinance_warning_still_builds() -> None:
    pack = FinancingPack()
    snap = _twin()
    resolved = pack.resolve_defaults(
        snap,
        {
            "loan_name": "Refi",
            "principal": "30000",
            "disbursement_year_month": "2027-01",
            "annual_rate": "0.04",
            "term_months": 12,
            "use_of_funds": "refinance_placeholder",
            "horizon_months": 12,
        },
    )
    issues = pack.validate_inputs(resolved)
    assert not has_errors(issues)
    assert any(i.code == "refinance_placeholder" for i in issues)
    bundle = pack.build(snap, resolved)
    pr = run_variant(snap, bundle.variants["base"])
    assert pr.result.cash_flow[0].loan_drawdowns == D(30000)
    # existing twin loans untouched (none); snapshot not mutated
    assert snap.loans == ()


def test_financing_actual_keys_include_capex() -> None:
    assert "capex_total" in FinancingPack().actual_keys()
    assert "min_cash" in FinancingPack().actual_keys()


def test_asset_purchase_loan_mode() -> None:
    pack = AssetPurchasePack()
    snap = _twin()
    bundle = pack.build(
        snap,
        {
            "asset_name": "Horno",
            "acquisition_cost": "40000",
            "acquisition_year_month": "2027-01",
            "useful_life_months": 60,
            "funding_mode": "loan",
            "loan_annual_rate": "0.06",
            "loan_term_months": 36,
            "horizon_months": 24,
            "discount_rate_annual": "0.08",
        },
    )
    pr = run_variant(snap, bundle.variants["base"])
    assert pr.result.cash_flow[0].capex_paid == D(40000)
    assert pr.result.cash_flow[0].loan_drawdowns == D(40000)
    # adverse scales CAPEX
    adv = run_variant(snap, bundle.variants["adverse"])
    assert adv.result.cash_flow[0].capex_paid == D(40000) * D("1.10")


def test_asset_compare_funding_modes() -> None:
    pack = AssetPurchasePack()
    snap = _twin()
    bundle = pack.build(
        snap,
        {
            "asset_name": "Equipo",
            "acquisition_cost": "20000",
            "acquisition_year_month": "2027-01",
            "useful_life_months": 48,
            "funding_mode": "cash",
            "compare_funding_modes": True,
            "loan_annual_rate": "0.07",
            "loan_term_months": 24,
            "loan_principal": "20000",
            "leasing_monthly": "500",
            "leasing_term_months": 36,
            "horizon_months": 24,
            "discount_rate_annual": "0.08",
        },
    )
    assert set(bundle.variants) >= {"cash", "loan", "leasing_as_cost"}
    lease = run_variant(snap, bundle.variants["leasing_as_cost"])
    assert lease.result.cash_flow[0].capex_paid == D(0)
    cash = run_variant(snap, bundle.variants["cash"])
    assert cash.result.cash_flow[0].capex_paid == D(20000)


def test_hiring_adverse_has_no_uplift_stream() -> None:
    pack = HiringPack()
    snap = _twin()
    bundle = pack.build(
        snap,
        {
            "role_name": "Vendedor",
            "headcount": 1,
            "employer_cost_per_person": "2500",
            "start_year_month": "2027-01",
            "expected_monthly_revenue_uplift": "5000",
            "gross_margin_pct": "0.5",
            "horizon_months": 12,
            "discount_rate_annual": "0.08",
        },
    )
    base = run_variant(snap, bundle.variants["base"])
    adv = run_variant(snap, bundle.variants["adverse"])
    base_uplift = [s for s in base.mapped.calculation_input.revenue_streams if "Uplift" in s.name]
    adv_uplift = [s for s in adv.mapped.calculation_input.revenue_streams if "Uplift" in s.name]
    assert len(base_uplift) == 1
    assert len(adv_uplift) == 0
    # payroll still present in adverse
    assert len(adv.mapped.calculation_input.payroll) == 1


def test_generic_annual_benefit_cadence() -> None:
    pack = GenericInvestmentPack()
    snap = _twin()
    bundle = pack.build(
        snap,
        {
            "name": "AnnualBenefit",
            "capex_schedule": [{"year_month": "2027-01", "amount": "12000"}],
            "horizon_months": 12,
            "benefit_cadence": "annual",
            "benefit_amount": "12000",  # → 1000/month
            "benefit_type": "revenue",
            "gross_margin_pct": "1",
            "equity_amount": "12000",
            "discount_rate_annual": "0.08",
        },
    )
    pr = run_variant(snap, bundle.variants["base"])
    rev = next(s for s in pr.mapped.calculation_input.revenue_streams if "Benefit" in s.name)
    assert rev.base_monthly_revenue == D(1000)


def test_generic_funding_insufficient_error() -> None:
    pack = GenericInvestmentPack()
    issues = pack.validate_inputs(
        pack.resolve_defaults(
            _twin(),
            {
                "name": "X",
                "capex_schedule": [{"year_month": "2027-01", "amount": "100000"}],
                "horizon_months": 12,
                "benefit_cadence": "monthly",
                "benefit_amount": "100",
                "benefit_type": "opex_reduction",
                "debt_amount": "10000",
                "equity_amount": "5000",
                "loan_annual_rate": "0.05",
                "loan_term_months": 12,
                "discount_rate_annual": "0.08",
            },
        )
    )
    assert any(i.code == "funding_insufficient" for i in issues)


def test_liquidity_does_not_mutate_and_adverse_collection() -> None:
    pack = LiquidityPlanPack()
    snap = _twin()
    before_days = snap.revenue_streams[0].collection_days
    before_rev = snap.revenue_streams[0].base_monthly_revenue
    bundle = pack.build(
        snap,
        {
            "horizon_months": 6,
            "anchor_year_month": "2027-01",
            "sales_adjustment_pct": "0",
            "collection_days_delta": 0,
        },
    )
    assert snap.revenue_streams[0].collection_days == before_days
    assert snap.revenue_streams[0].base_monthly_revenue == before_rev
    adv = run_variant(snap, bundle.variants["adverse"])
    r0 = next(s for s in adv.mapped.effective_snapshot.revenue_streams if s.id == "R0")
    # adverse: sales -15%, collection +15
    assert r0.base_monthly_revenue == before_rev * D("0.85")
    assert r0.collection_days == before_days + 15


def test_all_f4_packs_deterministic_rebuild() -> None:
    snap = _twin()
    packs_inputs = [
        (
            FinancingPack(),
            {
                "loan_name": "L",
                "principal": "10000",
                "disbursement_year_month": "2027-01",
                "annual_rate": "0.05",
                "term_months": 12,
                "use_of_funds": "general",
                "horizon_months": 12,
            },
        ),
        (
            HiringPack(),
            {
                "role_name": "R",
                "headcount": 1,
                "employer_cost_per_person": "2000",
                "start_year_month": "2027-01",
                "horizon_months": 6,
                "discount_rate_annual": "0.08",
            },
        ),
    ]
    for pack, inputs in packs_inputs:
        a = pack.build(snap, inputs)
        b = pack.build(snap, inputs)
        assert a.variants["base"].build_ops[0].entity_id == b.variants["base"].build_ops[0].entity_id
        ha = run_variant(snap, a.variants["base"]).mapped.inputs_hash
        hb = run_variant(snap, b.variants["base"]).mapped.inputs_hash
        assert ha == hb
