"""F3 — new_site E2E (VALIDACION §5.2) + funding ERROR + no mutate snapshot."""

from financetwin_engine import NewSitePack, run_bundle, snapshot_from_dict
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.invariants import check_invariants
from financetwin_engine.mapper import ScenarioSpec, to_calculation_input
from financetwin_engine.packs.base import has_errors
from financetwin_engine.packs.new_site import ACTUAL_KEYS

_CANONICAL_KEYS = {
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


def _empty_twin():
    return snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {
                "currency": "EUR",
                "opening_cash": "80000",
                "default_purchase_payment_days": 0,
            },
            "fiscal": {
                "vat_rate": "0",
                "vat_settlement": "monthly",
                "vat_payment_lag_months": 0,
                "corp_tax_rate": "0",
                "corp_tax_payment_mode": "none",
            },
            "policies": {"min_cash": "0"},
        }
    )


def _canonical_inputs():
    """VALIDACION §5.2 / PRODUCTO: CAPEX 350k, ventas 40k, deuda 200k, equity 150k."""
    return {
        "site_name": "Tienda Alicante",
        "open_year_month": "2027-01",
        "capex_total": "350000",
        "sales_run_rate": "40000",
        "gross_margin_pct": "0.40",
        "rent_monthly": "4500",
        "other_opex_monthly": "1500",
        "headcount": 3,
        "employer_cost_per_person": "2800",
        "debt_amount": "200000",
        "equity_amount": "150000",
        "loan_term_months": 84,
        "loan_annual_rate": "0.055",
        "loan_grace_months": 0,
        "horizon_months": 36,
        "discount_rate_annual": "0.08",
        "collection_days": 0,
        "sales_ramp_months": 12,
    }


def test_funding_insufficient_is_error() -> None:
    pack = NewSitePack()
    inputs = _canonical_inputs()
    inputs["equity_amount"] = "50000"
    issues = pack.validate_inputs(pack.resolve_defaults(_empty_twin(), inputs))
    assert has_errors(issues)
    assert any(i.code == "funding_insufficient" for i in issues)
    try:
        pack.build(_empty_twin(), inputs)
        assert False, "build should raise on funding error"
    except ValueError:
        pass


def test_actual_keys_subset_of_modelo_catalog() -> None:
    pack = NewSitePack()
    assert set(pack.actual_keys()) <= _CANONICAL_KEYS
    assert set(ACTUAL_KEYS) <= _CANONICAL_KEYS


def test_build_does_not_mutate_snapshot() -> None:
    snap = _empty_twin()
    before_ops = len(snap.revenue_streams)
    before_cash = snap.company.opening_cash
    pack = NewSitePack()
    bundle = pack.build(snap, _canonical_inputs())
    assert len(snap.revenue_streams) == before_ops
    assert snap.company.opening_cash == before_cash
    assert set(bundle.variants) >= {"base", "conservative", "adverse"}
    assert len(bundle.variants["base"].build_ops) >= 5


def test_e2e_new_site_canonical() -> None:
    """VALIDACION §5.2."""
    snap = _empty_twin()
    pack = NewSitePack()
    bundle = pack.build(snap, _canonical_inputs())
    results = run_bundle(snap, bundle)

    assert set(results) == {"base", "conservative", "adverse"}
    hashes = {r.mapped.inputs_hash for r in results.values()}
    assert len(hashes) == 3

    base = results["base"]
    result = base.result
    assert result.horizon_months == 36
    assert result.investment_metrics is not None
    assert result.investment_metrics.npv is not None
    assert result.financing_need is not None
    assert result.financing_need.min_cash is not None
    assert len(result.policy_checks) >= 1

    check_invariants(
        result,
        assets=base.mapped.calculation_input.assets,
        loan_term_ends={},
    )

    assert result.cash_flow[0].capex_paid == D(350000)
    assert result.cash_flow[0].loan_drawdowns == D(200000)
    assert snap.revenue_streams == ()
    assert snap.loans == ()


def test_no_negative_cost_items_in_effective_snapshot() -> None:
    snap = _empty_twin()
    pack = NewSitePack()
    bundle = pack.build(snap, _canonical_inputs())
    for name, plan in bundle.variants.items():
        mapped = to_calculation_input(
            snap,
            ScenarioSpec(
                anchor_year_month=plan.anchor_year_month,
                horizon_months=plan.horizon_months,
                discount_rate_annual=plan.discount_rate_annual,
                overrides=plan.build_ops,
            ),
        )
        for c in mapped.effective_snapshot.cost_items:
            if c.amount_monthly is not None:
                assert c.amount_monthly >= D(0), f"{name} {c.id}"
