"""Auditoría F2 — BuildOps, huecos mapper, ADR 0001, invariantes fixture."""

from financetwin_engine import calculate
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.invariants import check_invariants
from financetwin_engine.mapper import (
    BuildOp,
    ScenarioSpec,
    SnapshotValidationError,
    apply_build_ops,
    snapshot_from_dict,
    to_calculation_input,
)


def _base_company(**extra):
    data = {
        "schema_version": "1.0",
        "company": {"currency": "EUR", "opening_cash": "10000"},
        "fiscal": {
            "vat_rate": "0",
            "vat_settlement": "monthly",
            "vat_payment_lag_months": 0,
            "corp_tax_rate": "0",
            "corp_tax_payment_mode": "none",
        },
    }
    data.update(extra)
    return snapshot_from_dict(data)


def test_apply_build_ops_does_not_mutate_base() -> None:
    snap = _base_company(
        revenue_streams=[
            {
                "id": "R1",
                "name": "s",
                "revenue_type": "recurring",
                "start_year_month": "2027-01",
                "base_monthly_revenue": "1000",
                "gross_margin_pct": "0.5",
                "collection_days": 0,
            }
        ]
    )
    before = snap.revenue_streams[0].base_monthly_revenue
    effective = apply_build_ops(
        snap,
        (
            BuildOp(
                op="set_field",
                entity_type="revenue_streams",
                entity_id="R1",
                field="base_monthly_revenue",
                value="9999",
            ),
        ),
    )
    assert snap.revenue_streams[0].base_monthly_revenue == before
    assert effective.revenue_streams[0].base_monthly_revenue == D(9999)


def test_add_entity_revenue_stream() -> None:
    snap = _base_company()
    effective = apply_build_ops(
        snap,
        (
            BuildOp(
                op="add_entity",
                entity_type="revenue_streams",
                entity_id="R-new",
                payload={
                    "id": "R-new",
                    "name": "nuevo",
                    "revenue_type": "recurring",
                    "start_year_month": "2027-01",
                    "base_monthly_revenue": "4000",
                    "gross_margin_pct": "0.4",
                    "collection_days": 30,
                },
            ),
        ),
    )
    assert len(effective.revenue_streams) == 1
    assert effective.revenue_streams[0].id == "R-new"


def test_start_after_horizon_excluded() -> None:
    snap = _base_company(
        revenue_streams=[
            {
                "id": "R1",
                "name": "future",
                "revenue_type": "recurring",
                "start_year_month": "2028-06",
                "base_monthly_revenue": "1000",
                "gross_margin_pct": "0.5",
                "collection_days": 0,
            }
        ]
    )
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=12,  # ends 2027-12
            discount_rate_annual=D(0),
        ),
    )
    assert mapped.calculation_input.revenue_streams == ()


def test_pre_anchor_loan_skip_drawdown() -> None:
    """ADR 0001: préstamo ya dispuesto no inyecta caja en t=0."""
    snap = _base_company(
        loans=[
            {
                "id": "L1",
                "name": "old",
                "principal": "120000",
                "annual_interest_rate": "0.12",
                "term_months": 12,
                "amortization_system": "french",
                "grace_months": 0,
                "grace_type": "none",
                "disbursement_year_month": "2026-01",
            }
        ]
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
    assert loan.skip_drawdown is True
    result = calculate(mapped.calculation_input)
    assert result.cash_flow[0].loan_drawdowns == D(0)
    assert result.pnl[0].interest_expense == D(1200)


def test_own_funds_duplicate_with_explicit_equity_rejected() -> None:
    snap = _base_company(
        investments=[
            {
                "id": "I1",
                "name": "p",
                "capex_schedule": [
                    {"year_month": "2027-01", "amount": "10000", "includes_vat": False}
                ],
                "analysis_start_year_month": "2027-01",
                "analysis_horizon_months": 12,
                "own_funds_year_month": "2027-01",
                "own_funds_amount": "5000",
            }
        ],
        one_off_cash_events=[
            {
                "id": "E1",
                "year_month": "2027-01",
                "amount": "5000",
                "kind": "equity_injection",
            }
        ],
    )
    try:
        to_calculation_input(
            snap,
            ScenarioSpec(
                anchor_year_month="2027-01",
                horizon_months=12,
                discount_rate_annual=D(0),
            ),
        )
        assert False, "expected SnapshotValidationError"
    except SnapshotValidationError as e:
        assert "duplicate own_funds" in str(e)


def test_grace_capital_maps_to_motor() -> None:
    snap = _base_company(
        loans=[
            {
                "id": "L1",
                "name": "g",
                "principal": "100000",
                "annual_interest_rate": "0.12",
                "term_months": 12,
                "amortization_system": "french",
                "grace_months": 3,
                "grace_type": "capital",
                "disbursement_year_month": "2027-01",
            }
        ]
    )
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=15,
            discount_rate_annual=D(0),
        ),
    )
    loan = mapped.calculation_input.loans[0]
    assert loan.grace_months == 3
    assert loan.grace_type == "capital"
    result = calculate(mapped.calculation_input)
    assert result.loan_schedules["L1"].rows[0].principal_repaid == D(0)
    assert result.loan_schedules["L1"].rows[0].interest_paid == D(1000)


def test_store_loan_invariants_via_mapper() -> None:
    from tests.unit.test_mapper_m1_m7 import _store_loan_fixture

    snap = _store_loan_fixture()
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=24,
            discount_rate_annual=D("0.08"),
        ),
    )
    result = calculate(mapped.calculation_input)
    check_invariants(
        result,
        assets=mapped.calculation_input.assets,
        loan_term_ends={"L1": 23},
    )
    assert result.cash_flow[0].capex_paid == D(60000)
    assert result.cash_flow[0].loan_drawdowns == D(60000)


def test_reject_non_eur_currency() -> None:
    try:
        snapshot_from_dict(
            {
                "schema_version": "1.0",
                "company": {"currency": "USD", "opening_cash": "0"},
            }
        )
        assert False
    except SnapshotValidationError:
        pass


def test_mapper_inputs_hash_matches_calculate() -> None:
    snap = _base_company(
        revenue_streams=[
            {
                "id": "R1",
                "name": "s",
                "revenue_type": "recurring",
                "start_year_month": "2027-01",
                "base_monthly_revenue": "1000",
                "gross_margin_pct": "1",
                "collection_days": 0,
            }
        ]
    )
    mapped = to_calculation_input(
        snap,
        ScenarioSpec(
            anchor_year_month="2027-01",
            horizon_months=3,
            discount_rate_annual=D(0),
        ),
    )
    result = calculate(mapped.calculation_input)
    assert mapped.inputs_hash == result.inputs_hash
