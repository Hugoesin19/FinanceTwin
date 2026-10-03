"""Run a BuiltScenarioBundle variant through mapper + motor (pure, no I/O)."""

from __future__ import annotations

from dataclasses import dataclass

from financetwin_engine.calc.engine import calculate
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot
from financetwin_engine.mapper.to_input import MappedCalculation, ScenarioSpec, to_calculation_input
from financetwin_engine.model.calculation import CalculationResult
from financetwin_engine.packs.base import BuiltScenarioBundle, VariantPlan


@dataclass(frozen=True)
class PackVariantResult:
    variant_name: str
    mapped: MappedCalculation
    result: CalculationResult


def run_variant(
    snapshot: CompanyTwinSnapshot,
    variant: VariantPlan,
) -> PackVariantResult:
    """Aplica build_ops en memoria (sin mutar snapshot) y calcula."""
    mapped = to_calculation_input(
        snapshot,
        ScenarioSpec(
            anchor_year_month=variant.anchor_year_month,
            horizon_months=variant.horizon_months,
            discount_rate_annual=variant.discount_rate_annual,
            auto_finance_deficits=variant.auto_finance_deficits,
            overrides=variant.build_ops,
        ),
    )
    result = calculate(mapped.calculation_input)
    return PackVariantResult(
        variant_name=variant.name,
        mapped=mapped,
        result=result,
    )


def run_bundle(
    snapshot: CompanyTwinSnapshot,
    bundle: BuiltScenarioBundle,
) -> dict[str, PackVariantResult]:
    return {
        name: run_variant(snapshot, plan) for name, plan in bundle.variants.items()
    }
