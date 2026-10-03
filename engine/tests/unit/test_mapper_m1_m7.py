"""VALIDACION L1 — M1–M7 + fixture tienda+préstamo."""

from financetwin_engine import calculate
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper import (
    BuildOp,
    ScenarioSpec,
    SnapshotValidationError,
    months_between,
    snapshot_from_dict,
    to_calculation_input,
)


def test_m1_months_between() -> None:
    assert months_between("2027-01", "2027-01") == 0
    assert months_between("2027-01", "2027-09") == 8
    assert months_between("2027-01", "2026-10") == -3


def test_m2_start_before_anchor_active_becomes_t0() -> None:
    snap = snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {"currency": "EUR", "opening_cash": "10000"},
            "revenue_streams": [
                {
                    "id": "R1",
                    "name": "sales",
                    "revenue_type": "recurring",
                    "start_year_month": "2026-01",  # before anchor
                    "base_monthly_revenue": "5000",
                    "gross_margin_pct": "0.4",
                    "collection_days": 0,
                }
            ],
        }
    )
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=12,
            discount_rate_annual=D("0.08"),
        ),
    )
    assert len(mapped.calculation_input.revenue_streams) == 1
    assert mapped.calculation_input.revenue_streams[0].start_t == 0


def test_m3_end_before_anchor_excluded() -> None:
    snap = snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {"currency": "EUR", "opening_cash": "10000"},
            "revenue_streams": [
                {
                    "id": "R1",
                    "name": "closed",
                    "revenue_type": "recurring",
                    "start_year_month": "2025-01",
                    "end_year_month": "2026-06",
                    "base_monthly_revenue": "5000",
                    "gross_margin_pct": "0.4",
                    "collection_days": 0,
                }
            ],
        }
    )
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=12,
            discount_rate_annual=D(0),
        ),
    )
    assert mapped.calculation_input.revenue_streams == ()


def test_m4_grace_none_not_sent_to_motor() -> None:
    snap = snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {"currency": "EUR", "opening_cash": "0"},
            "loans": [
                {
                    "id": "L1",
                    "name": "loan",
                    "principal": "100000",
                    "annual_interest_rate": "0.06",
                    "term_months": 12,
                    "amortization_system": "french",
                    "grace_months": 0,
                    "grace_type": "none",
                    "disbursement_year_month": "2027-01",
                }
            ],
        }
    )
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=12,
            discount_rate_annual=D(0),
        ),
    )
    loan = mapped.calculation_input.loans[0]
    assert loan.grace_months == 0
    assert loan.grace_type != "none"


def test_m5_own_funds_single_equity_injection() -> None:
    snap = snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {"currency": "EUR", "opening_cash": "50000"},
            "investments": [
                {
                    "id": "I1",
                    "name": "store",
                    "capex_schedule": [
                        {"year_month": "2027-01", "amount": "100000", "includes_vat": False}
                    ],
                    "linked_asset_ids": [],
                    "analysis_start_year_month": "2027-01",
                    "analysis_horizon_months": 36,
                    "own_funds_year_month": "2027-01",
                    "own_funds_amount": "40000",
                }
            ],
        }
    )
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=12,
            discount_rate_annual=D("0.08"),
        ),
    )
    equity = [
        o
        for o in mapped.calculation_input.one_off_cash_events
        if o.kind == "equity_injection"
    ]
    assert len(equity) == 1
    assert equity[0].amount == D(40000)
    assert equity[0].t == 0
    assert equity[0].id.startswith("own_funds::")


def test_m6_asset_investment_incoherent_rejected() -> None:
    try:
        snapshot_from_dict(
            {
                "schema_version": "1.0",
                "company": {"currency": "EUR", "opening_cash": "0"},
                "assets": [
                    {
                        "id": "A1",
                        "name": "fitout",
                        "acquisition_cost": "50000",
                        "acquisition_year_month": "2027-01",
                        "useful_life_months": 60,
                        "depreciation_method": "straight_line",
                        "acquisition_funding": "cash",
                        "investment_id": "I1",
                    }
                ],
                "investments": [
                    {
                        "id": "I1",
                        "name": "proj",
                        "capex_schedule": [
                            {
                                "year_month": "2027-01",
                                "amount": "50000",
                                "includes_vat": False,
                            }
                        ],
                        "linked_asset_ids": [],  # missing A1
                        "analysis_start_year_month": "2027-01",
                        "analysis_horizon_months": 24,
                    }
                ],
            }
        )
        assert False, "expected SnapshotValidationError"
    except SnapshotValidationError:
        pass


def test_m7_same_snapshot_scenario_same_inputs_hash() -> None:
    snap = _store_loan_fixture()
    scenario = ScenarioSpec(
        anchor_year_month="2027-01",
        horizon_months=24,
        discount_rate_annual=D("0.08"),
    )
    a = to_calculation_input(snap, scenario)
    b = to_calculation_input(snap, scenario)
    assert a.inputs_hash == b.inputs_hash
    r1 = calculate(a.calculation_input)
    r2 = calculate(b.calculation_input)
    assert r1.inputs_hash == r2.inputs_hash
    assert r1.result_hash == r2.result_hash


def test_schema_rejects_bad_version() -> None:
    try:
        snapshot_from_dict(
            {
                "schema_version": "9.9",
                "company": {"currency": "EUR", "opening_cash": "0"},
            }
        )
        assert False
    except SnapshotValidationError:
        pass


def test_store_loan_fixture_calculate_ok() -> None:
    """DoD F2: tienda + préstamo → calculate() acepta el input."""
    snap = _store_loan_fixture()
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=24,
            discount_rate_annual=D("0.08"),
            overrides=(
                BuildOp(
                    op="set_field",
                    entity_type="company",
                    field="opening_cash",
                    value="55000",
                ),
            ),
        ),
    )
    result = calculate(mapped.calculation_input)
    assert result.horizon_months == 24
    assert mapped.calculation_input.company.opening_cash == D(55000)
    assert len(mapped.calculation_input.loans) == 1
    assert len(mapped.calculation_input.revenue_streams) == 1


def _store_loan_fixture():
    return snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {
                "currency": "EUR",
                "opening_cash": "50000",
                "default_purchase_payment_days": 30,
            },
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
                    "id": "R-store",
                    "name": "Tienda",
                    "revenue_type": "recurring",
                    "start_year_month": "2027-01",
                    "base_monthly_revenue": "20000",
                    "gross_margin_pct": "0.40",
                    "collection_days": 0,
                    "origin": "user",
                    "confidence": "medium",
                }
            ],
            "cost_items": [
                {
                    "id": "C-rent",
                    "name": "Alquiler",
                    "nature": "fixed",
                    "start_year_month": "2027-01",
                    "amount_monthly": "3000",
                    "payment_days": 0,
                }
            ],
            "payroll": [
                {
                    "id": "P1",
                    "role_name": "dependiente",
                    "headcount": 2,
                    "monthly_employer_cost": "2200",
                    "start_year_month": "2027-01",
                    "payment_days": 0,
                }
            ],
            "loans": [
                {
                    "id": "L1",
                    "name": "Préstamo tienda",
                    "principal": "60000",
                    "annual_interest_rate": "0.06",
                    "term_months": 24,
                    "amortization_system": "french",
                    "grace_months": 0,
                    "grace_type": "none",
                    "disbursement_year_month": "2027-01",
                    "origination_fee": "0",
                }
            ],
            "assets": [
                {
                    "id": "A1",
                    "name": "Acondicionamiento",
                    "acquisition_cost": "60000",
                    "acquisition_year_month": "2027-01",
                    "useful_life_months": 60,
                    "depreciation_method": "straight_line",
                    "acquisition_funding": "loan",
                    "funding_loan_id": "L1",
                    "investment_id": "I1",
                }
            ],
            "investments": [
                {
                    "id": "I1",
                    "name": "Apertura tienda",
                    "capex_schedule": [
                        {
                            "year_month": "2027-01",
                            "amount": "60000",
                            "includes_vat": False,
                        }
                    ],
                    "linked_asset_ids": ["A1"],
                    "linked_loan_ids": ["L1"],
                    "analysis_start_year_month": "2027-01",
                    "analysis_horizon_months": 24,
                }
            ],
        }
    )
