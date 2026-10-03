"""Golden G1 / G2 — MOTOR §14."""

from decimal import Decimal

from financetwin_engine import calculate_investment_metrics
from financetwin_engine.calc.decimal_money import D


def test_g1_van_known_zero_rate() -> None:
    """G1 — VAN r=0, payback simple T=3."""
    fc = [D(-1000), D(400), D(400), D(400)]
    metrics = calculate_investment_metrics(fc, discount_rate_annual=D(0))

    assert metrics.npv == D(200)
    assert metrics.payback_simple == 3


def test_g2_van_with_discount() -> None:
    """G2 — r_month=0.01 → VAN 18.22 (ROUND_HALF_UP)."""
    # r_month = 0.01 ⇒ r_annual = (1.01)^12 - 1  (MOTOR §10.2)
    r_month = D("0.01")
    discount_rate_annual = (D(1) + r_month) ** 12 - D(1)

    fc = [D(-100), D(60), D(60)]
    metrics = calculate_investment_metrics(fc, discount_rate_annual=discount_rate_annual)

    assert metrics.npv == D("18.22")


def test_rejects_float_cash_flows() -> None:
    try:
        calculate_investment_metrics([-100.0, 60.0], Decimal("0"))  # type: ignore[list-item]
        assert False, "expected TypeError"
    except TypeError:
        pass
