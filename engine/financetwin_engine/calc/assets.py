"""Asset depreciation — MOTOR §7.4."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.model.asset import Asset

ZERO = D(0)


@dataclass(frozen=True)
class AssetDepreciationRow:
    t: int
    depreciation: Decimal
    cumulative_depreciation: Decimal
    net_book_value: Decimal


def build_asset_depreciation(asset: Asset, horizon: int) -> tuple[AssetDepreciationRow, ...]:
    """Straight-line (and declining_simple) depreciation schedule."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if isinstance(asset.acquisition_cost, float):
        raise TypeError("Asset money fields must use Decimal, not float")

    rows: list[AssetDepreciationRow] = []
    cumulative = ZERO
    nbv = money(asset.acquisition_cost)
    depreciable_base = money(asset.acquisition_cost - asset.residual_value)

    if asset.depreciation_method == "straight_line":
        if asset.useful_life_months < 1:
            raise ValueError("useful_life_months must be >= 1")
        dep_monthly = money(depreciable_base / D(asset.useful_life_months))
        last_t = asset.acquisition_t + asset.useful_life_months - 1

        for t in range(horizon):
            dep = ZERO
            if asset.acquisition_t <= t <= last_t and cumulative < depreciable_base:
                if t == last_t:
                    dep = money(depreciable_base - cumulative)
                else:
                    dep = dep_monthly
                    if cumulative + dep > depreciable_base:
                        dep = money(depreciable_base - cumulative)
            cumulative = money(cumulative + dep)
            nbv = money(asset.acquisition_cost - cumulative)
            rows.append(
                AssetDepreciationRow(
                    t=t,
                    depreciation=dep,
                    cumulative_depreciation=cumulative,
                    net_book_value=nbv,
                )
            )
        return tuple(rows)

    if asset.depreciation_method == "declining_simple":
        rate = D(2) / D(asset.useful_life_months)
        for t in range(horizon):
            dep = ZERO
            if t >= asset.acquisition_t and nbv > asset.residual_value:
                dep = money(nbv * rate)
                max_dep = money(nbv - asset.residual_value)
                if dep > max_dep:
                    dep = max_dep
            cumulative = money(cumulative + dep)
            nbv = money(nbv - dep)
            rows.append(
                AssetDepreciationRow(
                    t=t,
                    depreciation=dep,
                    cumulative_depreciation=cumulative,
                    net_book_value=nbv,
                )
            )
        return tuple(rows)

    raise ValueError(f"unsupported depreciation_method: {asset.depreciation_method}")


def depreciation_at(asset: Asset, t: int) -> Decimal:
    """Depreciation amount for a single month t."""
    horizon = max(t + 1, asset.acquisition_t + asset.useful_life_months)
    rows = build_asset_depreciation(asset, horizon)
    return rows[t].depreciation
