"""Golden G3 / G4 / G5 — MOTOR §14 loan schedules."""

from financetwin_engine import Loan, build_loan_schedule
from financetwin_engine.calc.decimal_money import D


def _french_loan(**kwargs):
    defaults = dict(
        id="L1",
        name="test",
        principal=D(120000),
        annual_interest_rate=D("0.12"),
        term_months=12,
        amortization_system="french",
        disbursement_t=0,
        grace_months=0,
        origination_fee=D(0),
    )
    defaults.update(kwargs)
    return Loan(**defaults)


def test_g3_french_no_grace() -> None:
    """G3 — francés sin carencia."""
    loan = _french_loan()
    schedule = build_loan_schedule(loan, horizon=12)
    rows = schedule.rows

    assert len(rows) == 12
    assert rows[0].interest_accrued == D(1200)
    assert rows[0].interest_paid == D(1200)
    assert rows[0].drawdown == D(120000)

    # cuota constante salvo posible ajuste última
    payments = [r.payment for r in rows]
    assert all(p == payments[0] for p in payments[:-1])

    assert rows[-1].closing_principal == D(0)
    assert sum((r.principal_repaid for r in rows), D(0)) == D(120000)


def test_g4_capital_grace_3_months() -> None:
    """G4 — carencia de capital 3 meses + 12 cuotas francesas."""
    loan = _french_loan(grace_months=3, grace_type="capital")
    schedule = build_loan_schedule(loan, horizon=15)
    rows = schedule.rows

    for t in range(3):
        assert rows[t].interest_paid == D(1200)
        assert rows[t].principal_repaid == D(0)
        assert rows[t].closing_principal == D(120000)

    amort = rows[3:15]
    assert len(amort) == 12
    assert amort[0].opening_principal == D(120000)
    assert amort[-1].closing_principal == D(0)
    assert sum((r.principal_repaid for r in amort), D(0)) == D(120000)


def test_g5_total_grace_2_months() -> None:
    """G5 — carencia total 2 meses; gasto financiero sin pago de intereses."""
    loan = Loan(
        id="L2",
        name="total-grace",
        principal=D(100000),
        annual_interest_rate=D("0.12"),
        term_months=12,
        amortization_system="french",
        grace_months=2,
        grace_type="total",
        disbursement_t=0,
        origination_fee=D(0),
    )
    schedule = build_loan_schedule(loan, horizon=14)
    rows = schedule.rows

    # t=0: D=100000, interest_expense=1000, paid=0, D→101000
    assert rows[0].interest_paid == D(0)
    assert rows[0].interest_accrued == D(1000)
    assert rows[0].closing_principal == D(101000)

    # t=1: D=101000, interest=1010, paid=0, D→102010
    assert rows[1].interest_paid == D(0)
    assert rows[1].interest_accrued == D(1010)
    assert rows[1].closing_principal == D(102010)

    amort = rows[2:14]
    assert amort[0].opening_principal == D(102010)
    assert amort[-1].closing_principal == D(0)
    assert sum((r.principal_repaid for r in amort), D(0)) == D(102010)
