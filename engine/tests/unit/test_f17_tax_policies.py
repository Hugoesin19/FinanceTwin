"""F1.7 — taxes, policies, financing_need (MOTOR §9, §11–12)."""

from financetwin_engine import (
    CalculationInput,
    CompanyInput,
    CompanyPolicy,
    FiscalConfig,
    RevenueStream,
    calculate,
)
from financetwin_engine.calc.decimal_money import D


def test_corp_tax_accrual_and_annual_payment() -> None:
    """Impuesto sociedades: gasto en P&L; pago annual_end en último mes."""
    inp = CalculationInput(
        company=CompanyInput(
            opening_cash=D(100000),
            default_purchase_payment_days=0,
            fiscal=FiscalConfig(
                vat_rate=D(0),
                corp_tax_rate=D("0.25"),
                corp_tax_payment_mode="annual_end",
            ),
        ),
        horizon_months=3,
        revenue_streams=(
            RevenueStream(
                id="R1",
                name="sales",
                start_t=0,
                base_monthly_revenue=D(10000),
                gross_margin_pct=D(1),
                collection_days=0,
            ),
        ),
    )
    result = calculate(inp)
    # ebit ≈ 10000, tax 2500/mes
    assert result.pnl[0].corp_tax_expense == D(2500)
    assert result.pnl[0].net_income == D(7500)
    assert result.cash_flow[0].corp_tax_paid == D(0)
    assert result.cash_flow[1].corp_tax_paid == D(0)
    assert result.cash_flow[2].corp_tax_paid == D(7500)  # 3 * 2500


def test_policy_min_cash_fail_and_financing_need() -> None:
    from financetwin_engine.model.one_off import OneOffCashEvent

    inp = CalculationInput(
        company=CompanyInput(
            opening_cash=D(150),
            policies=CompanyPolicy(min_cash=D(0)),
        ),
        horizon_months=4,
        one_off_cash_events=tuple(
            OneOffCashEvent(id=f"O{t}", t=t, amount=D(50), kind="other_out")
            for t in range(4)
        ),
    )
    result = calculate(inp)
    assert result.financing_need.first_shortfall_month == 3
    assert result.financing_need.max_shortfall_vs_policy == D(50)
    min_cash_check = next(c for c in result.policy_checks if c.policy_id == "min_cash")
    assert min_cash_check.status == "fail"


def test_vat_monthly_payment_with_lag() -> None:
    inp = CalculationInput(
        company=CompanyInput(
            opening_cash=D(0),
            default_purchase_payment_days=0,
            fiscal=FiscalConfig(
                vat_rate=D("0.21"),
                vat_settlement="monthly",
                vat_payment_lag_months=1,
                corp_tax_rate=D(0),
            ),
        ),
        horizon_months=2,
        revenue_streams=(
            RevenueStream(
                id="R1",
                name="sales",
                start_t=0,
                end_t=0,
                base_monthly_revenue=D(1000),
                gross_margin_pct=D(1),
                collection_days=0,
            ),
        ),
    )
    result = calculate(inp)
    # vat_output t0 = 210; paid with lag 1 → t1
    assert result.cash_flow[0].vat_paid == D(0)
    assert result.cash_flow[1].vat_paid == D(210)
