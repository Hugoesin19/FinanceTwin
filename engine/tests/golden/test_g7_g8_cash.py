"""Golden G7 / G8 — MOTOR §14 cash lags and shortfall."""

from financetwin_engine.calc.cash import build_cash_flow_series, compute_financing_need
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.pnl import build_pnl_series
from financetwin_engine.model import CostItem, OneOffCashEvent, RevenueStream


def test_g7_collection_lag_30_days() -> None:
    """G7 — collection_days=30 → lag=1; AR then cash."""
    streams = [
        RevenueStream(
            id="R1",
            name="sales",
            start_t=0,
            end_t=0,  # solo t=0 (G7)
            base_monthly_revenue=D(10000),
            gross_margin_pct=D(1),  # cogs=0
            collection_days=30,
        )
    ]
    # margin 100% → cogs=0; no costs
    pnl = build_pnl_series(horizon=2, revenue_streams=streams)
    cash = build_cash_flow_series(
        pnl=pnl,
        revenue_streams=streams,
        opening_cash=D(0),
        vat_rate=D(0),
        default_purchase_payment_days=0,
    )

    assert cash[0].collections == D(0)
    assert cash[1].collections == D(10000)
    assert cash[0].closing_cash == D(0)
    assert cash[1].closing_cash == D(10000)
    assert cash[0].accounts_receivable == D(10000)
    assert cash[1].accounts_receivable == D(0)


def test_g8_min_cash_and_shortfall() -> None:
    """G8 — closing_cash = -50 en t=3; policy min=0 → max_shortfall=50."""
    # opening 150; other_out 50 cada mes → t=3 closing -50
    one_offs = [
        OneOffCashEvent(id=f"O{t}", t=t, amount=D(50), kind="other_out")
        for t in range(4)
    ]
    pnl = build_pnl_series(horizon=4)  # todo cero
    cash = build_cash_flow_series(
        pnl=pnl,
        opening_cash=D(150),
        one_offs=one_offs,
    )

    assert cash[3].closing_cash == D(-50)
    need = compute_financing_need(cash, policy_min_cash=D(0))
    assert need.max_shortfall_vs_policy == D(50)
    assert need.first_shortfall_month == 3
