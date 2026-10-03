"""Loan amortization schedules — MOTOR §7.5."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.model.loan import Loan

ZERO = D(0)
ONE = D(1)
TWELVE = D(12)


@dataclass(frozen=True)
class LoanScheduleRow:
    t: int
    opening_principal: Decimal
    drawdown: Decimal
    interest_accrued: Decimal
    interest_paid: Decimal
    principal_repaid: Decimal
    payment: Decimal
    origination_fee_paid: Decimal
    closing_principal: Decimal


@dataclass(frozen=True)
class LoanSchedule:
    loan_id: str
    rows: tuple[LoanScheduleRow, ...]


def _monthly_rate(annual_interest_rate: Decimal) -> Decimal:
    """i = annual_interest_rate / 12 — TIN/12 (MOTOR §7.5)."""
    return annual_interest_rate / TWELVE


def _french_payment(principal: Decimal, i: Decimal, n: int) -> Decimal:
    if n <= 0:
        raise ValueError("term_months must be >= 1")
    if i == ZERO:
        return money(principal / D(n))
    # payment = P * i / (1 - (1+i)^(-n))
    return money(principal * i / (ONE - (ONE + i) ** D(-n)))


def build_loan_schedule(loan: Loan, horizon: int) -> LoanSchedule:
    """Utilidad pura — MOTOR §16 / §7.5."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if isinstance(loan.principal, float) or isinstance(loan.annual_interest_rate, float):
        raise TypeError("Loan money/rate fields must use Decimal, not float")

    i = _monthly_rate(loan.annual_interest_rate)
    rows: list[LoanScheduleRow] = []

    # Principal vivo al inicio del mes (antes de cuota). Antes de disposición: 0.
    outstanding = ZERO
    amort_start = loan.disbursement_t + loan.grace_months
    amort_end = amort_start + loan.term_months  # exclusive end index of amort months
    amort_principal: Decimal | None = None
    french_payment: Decimal | None = None
    linear_principal_share: Decimal | None = None
    amort_month_index = 0  # 0..term_months-1 within amortization

    for t in range(horizon):
        drawdown = ZERO
        fee = ZERO
        interest_accrued = ZERO
        interest_paid = ZERO
        principal_repaid = ZERO
        payment = ZERO
        opening = outstanding

        if t == loan.disbursement_t:
            if not loan.skip_drawdown:
                drawdown = money(loan.principal)
            outstanding = money(loan.principal)
            opening = outstanding
            if loan.origination_fee > ZERO and not loan.skip_drawdown:
                fee = money(loan.origination_fee)

        in_grace = (
            loan.grace_months > 0
            and loan.disbursement_t <= t < amort_start
            and outstanding > ZERO
        )
        in_amort = amort_start <= t < amort_end and outstanding > ZERO

        if in_grace:
            if loan.grace_type == "capital":
                interest_accrued = money(outstanding * i)
                interest_paid = interest_accrued
                principal_repaid = ZERO
                payment = interest_paid
                # D stays
            elif loan.grace_type == "total":
                interest_accrued = money(outstanding * i)
                interest_paid = ZERO
                principal_repaid = ZERO
                payment = ZERO
                outstanding = money(outstanding + interest_accrued)
            else:
                raise ValueError(f"unsupported grace_type: {loan.grace_type}")

        elif in_amort:
            if amort_principal is None:
                amort_principal = outstanding
                if loan.amortization_system == "french":
                    french_payment = _french_payment(amort_principal, i, loan.term_months)
                elif loan.amortization_system == "linear":
                    linear_principal_share = money(amort_principal / D(loan.term_months))
                elif loan.amortization_system == "bullet":
                    pass
                else:
                    raise ValueError(
                        f"unsupported amortization_system: {loan.amortization_system}"
                    )

            is_last = amort_month_index == loan.term_months - 1

            if loan.amortization_system == "french":
                assert french_payment is not None
                interest_accrued = money(outstanding * i)
                interest_paid = interest_accrued
                if is_last:
                    principal_repaid = outstanding
                    payment = money(interest_paid + principal_repaid)
                else:
                    payment = french_payment
                    principal_repaid = money(payment - interest_paid)
                    if principal_repaid > outstanding:
                        principal_repaid = outstanding
                        payment = money(interest_paid + principal_repaid)
                outstanding = money(outstanding - principal_repaid)

            elif loan.amortization_system == "linear":
                assert linear_principal_share is not None
                interest_accrued = money(outstanding * i)
                interest_paid = interest_accrued
                if is_last:
                    principal_repaid = outstanding
                else:
                    principal_repaid = linear_principal_share
                payment = money(principal_repaid + interest_paid)
                outstanding = money(outstanding - principal_repaid)

            elif loan.amortization_system == "bullet":
                interest_accrued = money(outstanding * i)
                interest_paid = interest_accrued
                if is_last:
                    principal_repaid = outstanding
                    payment = money(principal_repaid + interest_paid)
                    outstanding = ZERO
                else:
                    principal_repaid = ZERO
                    payment = interest_paid

            amort_month_index += 1

        closing = outstanding
        rows.append(
            LoanScheduleRow(
                t=t,
                opening_principal=opening,
                drawdown=drawdown,
                interest_accrued=interest_accrued,
                interest_paid=interest_paid,
                principal_repaid=principal_repaid,
                payment=payment,
                origination_fee_paid=fee,
                closing_principal=closing,
            )
        )

    return LoanSchedule(loan_id=loan.id, rows=tuple(rows))
