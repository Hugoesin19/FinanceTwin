"""Golden G11 — MOTOR §14 anti doble CAPEX."""

from financetwin_engine.calc.capex import compute_capex_by_t
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.model import Asset, CapexPoint, Investment


def test_g11_anti_double_capex() -> None:
    """Asset 50k ligado a Investment con 50k en schedule → capex_0 = 50000 no 100000."""
    inv = Investment(
        id="I1",
        name="project",
        capex_schedule=(CapexPoint(t=0, amount=D(50000)),),
        linked_asset_ids=("A1",),
    )
    asset = Asset(
        id="A1",
        name="store fit-out",
        acquisition_cost=D(50000),
        acquisition_t=0,
        useful_life_months=60,
        investment_id="I1",
    )
    capex = compute_capex_by_t(horizon=1, investments=[inv], assets=[asset])
    assert capex[0] == D(50000)
