"""Snapshot → CalculationInput mapper (F2 / MODELO §11)."""

from financetwin_engine.mapper.build_ops import BuildOp, BuildOpError, apply_build_ops
from financetwin_engine.mapper.snapshot import (
    SCHEMA_VERSION,
    CompanyTwinSnapshot,
    SnapshotValidationError,
    snapshot_from_dict,
    validate_snapshot,
)
from financetwin_engine.mapper.time import add_months, months_between
from financetwin_engine.mapper.to_input import MappedCalculation, ScenarioSpec, to_calculation_input

__all__ = [
    "SCHEMA_VERSION",
    "BuildOp",
    "BuildOpError",
    "CompanyTwinSnapshot",
    "MappedCalculation",
    "ScenarioSpec",
    "SnapshotValidationError",
    "apply_build_ops",
    "months_between",
    "add_months",
    "snapshot_from_dict",
    "to_calculation_input",
    "validate_snapshot",
]
