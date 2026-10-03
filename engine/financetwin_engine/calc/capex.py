"""CAPEX aggregation with anti-double-count — MOTOR §8.2."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.model.asset import Asset
from financetwin_engine.model.investment import Investment
from financetwin_engine.model.one_off import OneOffCashEvent

ZERO = D(0)


def compute_capex_by_t(
    *,
    horizon: int,
    investments: Sequence[Investment] = (),
    assets: Sequence[Asset] = (),
    one_offs: Sequence[OneOffCashEvent] = (),
) -> tuple[Decimal, ...]:
    """
    capex_paid_t = Σ investment.capex_schedule
                 + Σ assets.acquisition_cost at acquisition_t
                   SOLO si el asset NO está ya incluido en un investment
                 + one_offs kind=capex
    """
    capex = [ZERO] * horizon

    linked_asset_ids: set[str] = set()
    for inv in investments:
        for aid in inv.linked_asset_ids:
            linked_asset_ids.add(aid)
        for pt in inv.capex_schedule:
            if 0 <= pt.t < horizon:
                capex[pt.t] = money(capex[pt.t] + pt.amount)

    for asset in assets:
        # Anti-doble: ligado a investment → no sumar acquisition_cost otra vez
        if asset.investment_id is not None or asset.id in linked_asset_ids:
            continue
        if 0 <= asset.acquisition_t < horizon:
            capex[asset.acquisition_t] = money(
                capex[asset.acquisition_t] + asset.acquisition_cost
            )

    for ev in one_offs:
        if ev.kind == "capex" and 0 <= ev.t < horizon:
            capex[ev.t] = money(capex[ev.t] + ev.amount)

    return tuple(capex)
