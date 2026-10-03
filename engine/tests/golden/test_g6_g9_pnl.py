"""Golden G6 / G9 — MOTOR §14 P&L and depreciation."""

from financetwin_engine.calc.assets import build_asset_depreciation
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.pnl import build_pnl_series
from financetwin_engine.model import Asset, CostItem, PayrollLine, RevenueStream


def test_g6_pnl_simple_one_month() -> None:
    """G6 — revenue 10k, margin 40%, payroll 2k, opex 1k → ebitda=ni=1000."""
    streams = [
        RevenueStream(
            id="R1",
            name="sales",
            start_t=0,
            base_monthly_revenue=D(10000),
            gross_margin_pct=D("0.40"),
        )
    ]
    costs = [
        CostItem(
            id="C1",
            name="opex",
            start_t=0,
            nature="fixed",
            amount_monthly=D(1000),
            payment_days=0,
        )
    ]
    payroll = [
        PayrollLine(
            id="P1",
            role_name="staff",
            headcount=1,
            monthly_employer_cost=D(2000),
            start_t=0,
        )
    ]
    pnl = build_pnl_series(
        horizon=1,
        revenue_streams=streams,
        cost_items=costs,
        payroll=payroll,
        corp_tax_rate=D(0),
    )[0]

    assert pnl.revenue == D(10000)
    assert pnl.cogs == D(6000)
    assert pnl.payroll_expense == D(2000)
    assert pnl.other_opex == D(1000)
    assert pnl.depreciation == D(0)
    assert pnl.interest_expense == D(0)
    assert pnl.ebitda == D(1000)
    assert pnl.net_income == D(1000)


def test_g9_straight_line_asset() -> None:
    """G9 — cost 1200, life 12 → dep 100 each month; cumulative 1200."""
    asset = Asset(
        id="A1",
        name="equip",
        acquisition_cost=D(1200),
        acquisition_t=0,
        useful_life_months=12,
        residual_value=D(0),
        depreciation_method="straight_line",
    )
    rows = build_asset_depreciation(asset, horizon=12)
    assert all(r.depreciation == D(100) for r in rows)
    assert rows[-1].cumulative_depreciation == D(1200)
