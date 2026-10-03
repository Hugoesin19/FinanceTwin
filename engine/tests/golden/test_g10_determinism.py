"""Golden G10 — MOTOR §14 determinism."""

from financetwin_engine import (
    CalculationInput,
    CompanyInput,
    Loan,
    calculate,
)
from financetwin_engine.calc.decimal_money import D


def _g3_input() -> CalculationInput:
    loan = Loan(
        id="L1",
        name="french",
        principal=D(120000),
        annual_interest_rate=D("0.12"),
        term_months=12,
        amortization_system="french",
        disbursement_t=0,
        grace_months=0,
        origination_fee=D(0),
    )
    return CalculationInput(
        company=CompanyInput(opening_cash=D(0)),
        horizon_months=12,
        loans=(loan,),
    )


def test_g10_determinism() -> None:
    """G10 — mismo input dos veces → mismos hashes."""
    inp = _g3_input()
    a = calculate(inp)
    b = calculate(inp)
    assert a.inputs_hash == b.inputs_hash
    assert a.result_hash == b.result_hash
    assert a.loan_schedules["L1"].rows[0].interest_accrued == D(1200)
