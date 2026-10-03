"""Auditoría F3 — new_site gaps / regresiones."""

from financetwin_engine import NewSitePack, run_bundle, run_variant, snapshot_from_dict
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.packs.base import has_errors


def _twin():
    return snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {"currency": "EUR", "opening_cash": "100000"},
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


def _base_inputs(**over):
    data = {
        "site_name": "Tienda Test",
        "open_year_month": "2027-06",
        "capex_total": "100000",
        "sales_run_rate": "20000",
        "gross_margin_pct": "0.40",
        "rent_monthly": "2000",
        "other_opex_monthly": "500",
        "debt_amount": "60000",
        "equity_amount": "40000",
        "loan_term_months": 24,
        "loan_annual_rate": "0.06",
        "horizon_months": 18,
        "discount_rate_annual": "0.08",
        "collection_days": 0,
        "sales_ramp_months": 6,
    }
    data.update(over)
    return data


def test_build_ids_deterministic_same_inputs() -> None:
    pack = NewSitePack()
    snap = _twin()
    a = pack.build(snap, _base_inputs())
    b = pack.build(snap, _base_inputs())
    assert a.variants["base"].build_ops[0].entity_id == b.variants["base"].build_ops[0].entity_id
    ra = run_variant(snap, a.variants["base"])
    rb = run_variant(snap, b.variants["base"])
    assert ra.mapped.inputs_hash == rb.mapped.inputs_hash
    assert ra.result.result_hash == rb.result.result_hash


def test_pre_open_shifts_anchor_and_defers_capex() -> None:
    pack = NewSitePack()
    snap = _twin()
    bundle = pack.build(snap, _base_inputs(pre_open_months=3))
    base = bundle.variants["base"]
    assert base.anchor_year_month == "2027-03"
    assert base.open_year_month == "2027-06"
    assert base.auto_finance_deficits is False
    result = run_variant(snap, base).result
    assert result.cash_flow[0].capex_paid == D(0)
    assert result.cash_flow[1].capex_paid == D(0)
    assert result.cash_flow[2].capex_paid == D(0)
    assert result.cash_flow[3].capex_paid == D(100000)


def test_adverse_open_plus_two_months() -> None:
    pack = NewSitePack()
    snap = _twin()
    bundle = pack.build(snap, _base_inputs(pre_open_months=0))
    assert bundle.variants["adverse"].open_year_month == "2027-08"
    assert bundle.variants["base"].open_year_month == "2027-06"


def test_funding_excess_is_warning_not_error() -> None:
    pack = NewSitePack()
    resolved = pack.resolve_defaults(
        _twin(),
        _base_inputs(equity_amount="50000", debt_amount="60000"),  # 110k > 100k
    )
    issues = pack.validate_inputs(resolved)
    assert not has_errors(issues)
    assert any(i.code == "funding_excess" for i in issues)


def test_headcount_requires_employer_cost() -> None:
    pack = NewSitePack()
    inputs = _base_inputs(headcount=2)
    inputs.pop("employer_cost_per_person", None)
    # resolve may fill from avg; empty twin has no payroll → remains missing
    resolved = pack.resolve_defaults(_twin(), inputs)
    issues = pack.validate_inputs(resolved)
    assert any(i.code == "missing_employer_cost" for i in issues)


def test_variants_have_distinct_sales() -> None:
    pack = NewSitePack()
    snap = _twin()
    results = run_bundle(snap, pack.build(snap, _base_inputs()))
    sales = {}
    for name, pr in results.items():
        # find new site revenue stream
        revs = pr.mapped.calculation_input.revenue_streams
        assert len(revs) == 1
        sales[name] = revs[0].base_monthly_revenue
    assert sales["conservative"] == D(20000) * D("0.85")
    assert sales["adverse"] == D(20000) * D("0.70")
    assert sales["base"] == D(20000)


def test_no_debt_path_cash_funded() -> None:
    pack = NewSitePack()
    snap = _twin()
    bundle = pack.build(
        snap,
        _base_inputs(debt_amount="0", equity_amount="100000"),
    )
    assert all(
        op.entity_type != "loans" for op in bundle.variants["base"].build_ops
    )
    result = run_variant(snap, bundle.variants["base"]).result
    assert result.cash_flow[0].loan_drawdowns == D(0)
    assert result.cash_flow[0].capex_paid == D(100000)
    assert result.cash_flow[0].equity_injections == D(100000)


def test_analysis_plan_present() -> None:
    plan = NewSitePack().analysis_plan()
    assert "sensitivity_vars" in plan
    assert "sales_run_rate" in plan["sensitivity_vars"]
