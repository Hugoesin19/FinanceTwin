"""Audit / regression tests before F2 — gaps found in F1 review."""

from decimal import Decimal

from financetwin_engine import (
    Asset,
    CalculationInput,
    CapexPoint,
    CompanyInput,
    CostItem,
    Investment,
    Loan,
    OneOffCashEvent,
    RevenueStream,
    calculate,
    calculate_investment_metrics,
)
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.invariants import check_invariants
from financetwin_engine.calc.loans import build_loan_schedule


def _walk_no_floats(obj, path="root") -> int:
    """Walk result tree; raise if float appears. Return Decimal field count."""
    if isinstance(obj, float):
        raise AssertionError(f"float found at {path}: {obj}")
    if isinstance(obj, Decimal):
        return 1
    count = 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            count += _walk_no_floats(v, f"{path}.{k}")
        return count
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            count += _walk_no_floats(v, f"{path}[{i}]")
        return count
    if hasattr(obj, "__dataclass_fields__"):
        for name in obj.__dataclass_fields__:
            count += _walk_no_floats(getattr(obj, name), f"{path}.{name}")
    return count


def test_linear_loan_schedule() -> None:
    loan = Loan(
        id="LIN",
        name="linear",
        principal=D(12000),
        annual_interest_rate=D("0.12"),
        term_months=12,
        amortization_system="linear",
    )
    rows = build_loan_schedule(loan, 12).rows
    assert rows[0].principal_repaid == D(1000)
    assert rows[0].interest_accrued == D(120)  # 12000 * 0.01
    assert rows[-1].closing_principal == D(0)
    assert sum((r.principal_repaid for r in rows), D(0)) == D(12000)


def test_bullet_loan_schedule() -> None:
    loan = Loan(
        id="BUL",
        name="bullet",
        principal=D(100000),
        annual_interest_rate=D("0.12"),
        term_months=6,
        amortization_system="bullet",
    )
    rows = build_loan_schedule(loan, 6).rows
    for r in rows[:-1]:
        assert r.principal_repaid == D(0)
        assert r.interest_paid == D(1000)
    assert rows[-1].principal_repaid == D(100000)
    assert rows[-1].closing_principal == D(0)


def test_g5_interest_expense_in_pnl_via_calculate() -> None:
    """G5 via calculate: carencia total → interest_expense > 0, interest_paid = 0."""
    loan = Loan(
        id="L2",
        name="total-grace",
        principal=D(100000),
        annual_interest_rate=D("0.12"),
        term_months=12,
        amortization_system="french",
        grace_months=2,
        grace_type="total",
    )
    result = calculate(
        CalculationInput(
            company=CompanyInput(opening_cash=D(0)),
            horizon_months=14,
            loans=(loan,),
        )
    )
    assert result.pnl[0].interest_expense == D(1000)
    assert result.cash_flow[0].loan_interest_paid == D(0)
    assert result.pnl[1].interest_expense == D(1010)
    assert result.cash_flow[1].loan_interest_paid == D(0)


def test_g11_capex_via_calculate_no_double() -> None:
    """G11 E2E: asset ligado + schedule → capex_paid_0 = 50000."""
    inv = Investment(
        id="I1",
        name="project",
        capex_schedule=(CapexPoint(t=0, amount=D(50000)),),
        linked_asset_ids=("A1",),
    )
    asset = Asset(
        id="A1",
        name="fitout",
        acquisition_cost=D(50000),
        acquisition_t=0,
        useful_life_months=60,
        investment_id="I1",
    )
    result = calculate(
        CalculationInput(
            company=CompanyInput(opening_cash=D(100000)),
            horizon_months=1,
            investments=(inv,),
            assets=(asset,),
        )
    )
    assert result.cash_flow[0].capex_paid == D(50000)


def test_one_off_capex_not_double_counted() -> None:
    """Regression: one_off capex no debe duplicarse con compute_capex_by_t."""
    result = calculate(
        CalculationInput(
            company=CompanyInput(opening_cash=D(100000)),
            horizon_months=1,
            one_off_cash_events=(
                OneOffCashEvent(id="CAP", t=0, amount=D(10000), kind="capex"),
            ),
        )
    )
    assert result.cash_flow[0].capex_paid == D(10000)
    assert result.cash_flow[0].closing_cash == D(90000)


def test_irr_zero_when_npv_zero_at_zero_rate() -> None:
    m = calculate_investment_metrics([D(-100), D(50), D(50)], D(0))
    assert m.npv == D(0)
    assert m.irr_annual is not None
    assert abs(m.irr_annual) < D("1e-8")


def test_irr_undefined_no_sign_change() -> None:
    m = calculate_investment_metrics([D(10), D(10), D(10)], D(0))
    assert m.irr_annual is None
    assert any("undefined" in w.lower() for w in m.warnings)


def test_result_contains_no_floats() -> None:
    loan = Loan(
        id="L1",
        name="f",
        principal=D(120000),
        annual_interest_rate=D("0.12"),
        term_months=12,
        amortization_system="french",
    )
    result = calculate(
        CalculationInput(
            company=CompanyInput(opening_cash=D(50000)),
            horizon_months=12,
            loans=(loan,),
        )
    )
    n = _walk_no_floats(result)
    assert n > 20


def test_invariants_on_g3_result() -> None:
    loan = Loan(
        id="L1",
        name="f",
        principal=D(120000),
        annual_interest_rate=D("0.12"),
        term_months=12,
        amortization_system="french",
    )
    result = calculate(
        CalculationInput(
            company=CompanyInput(opening_cash=D(0)),
            horizon_months=12,
            loans=(loan,),
        )
    )
    check_invariants(result, assets=(), loan_term_ends={"L1": 11})


def test_validation_rejects_duplicate_ids() -> None:
    try:
        calculate(
            CalculationInput(
                company=CompanyInput(opening_cash=D(0)),
                horizon_months=1,
                revenue_streams=(
                    RevenueStream(
                        id="X",
                        name="a",
                        start_t=0,
                        base_monthly_revenue=D(1),
                        gross_margin_pct=D("0.5"),
                    ),
                ),
                cost_items=(
                    CostItem(
                        id="X",
                        name="b",
                        start_t=0,
                        nature="fixed",
                        amount_monthly=D(1),
                    ),
                ),
            )
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert "duplicate" in str(e)
