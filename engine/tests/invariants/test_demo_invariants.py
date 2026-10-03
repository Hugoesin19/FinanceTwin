"""Invariants on a ≥24-month demo fixture — MOTOR §13 / PLAN F1.6."""

from financetwin_engine import (
    Asset,
    CalculationInput,
    CapexPoint,
    CompanyInput,
    CompanyPolicy,
    CostItem,
    FiscalConfig,
    Investment,
    Loan,
    PayrollLine,
    RevenueStream,
    calculate,
)
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.invariants import check_invariants


def _demo_input(horizon: int = 24) -> CalculationInput:
    return CalculationInput(
        company=CompanyInput(
            opening_cash=D(50000),
            default_purchase_payment_days=30,
            fiscal=FiscalConfig(vat_rate=D(0), corp_tax_rate=D(0)),
            policies=CompanyPolicy(min_cash=D(0)),
        ),
        horizon_months=horizon,
        discount_rate_annual=D("0.08"),
        revenue_streams=(
            RevenueStream(
                id="R1",
                name="retail",
                start_t=0,
                base_monthly_revenue=D(20000),
                gross_margin_pct=D("0.40"),
                collection_days=30,
            ),
        ),
        cost_items=(
            CostItem(
                id="C1",
                name="rent",
                start_t=0,
                nature="fixed",
                amount_monthly=D(3000),
                payment_days=0,
            ),
        ),
        payroll=(
            PayrollLine(
                id="P1",
                role_name="staff",
                headcount=2,
                monthly_employer_cost=D(2500),
                start_t=0,
            ),
        ),
        loans=(
            Loan(
                id="L1",
                name="capex loan",
                principal=D(60000),
                annual_interest_rate=D("0.06"),
                term_months=24,
                amortization_system="french",
                disbursement_t=0,
            ),
        ),
        assets=(
            Asset(
                id="A1",
                name="fitout",
                acquisition_cost=D(60000),
                acquisition_t=0,
                useful_life_months=60,
                investment_id="I1",
            ),
        ),
        investments=(
            Investment(
                id="I1",
                name="store",
                capex_schedule=(CapexPoint(t=0, amount=D(60000)),),
                linked_asset_ids=("A1",),
            ),
        ),
    )


def test_invariants_demo_24_months() -> None:
    inp = _demo_input(24)
    result = calculate(inp)
    check_invariants(
        result,
        assets=inp.assets,
        loan_term_ends={"L1": 23},
    )
    assert result.horizon_months == 24
    assert result.loan_schedules["L1"].rows[-1].closing_principal == D(0)
