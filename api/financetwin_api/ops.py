"""BuildOp / pack helpers for API layer."""

from __future__ import annotations

from typing import Any

from financetwin_api.serialize import to_jsonable
from financetwin_engine.mapper.build_ops import BuildOp
from financetwin_engine.packs.base import VariantPlan


def build_op_to_dict(op: BuildOp) -> dict[str, Any]:
    """Persistable BuildOp; Decimals → strings (MODELO §12 / §7.2)."""
    d: dict[str, Any] = {
        "op": op.op,
        "entity_type": op.entity_type,
    }
    if op.entity_id is not None:
        d["entity_id"] = op.entity_id
    if op.field is not None:
        d["field"] = op.field
    if op.value is not None:
        d["value"] = op.value
    if op.payload is not None:
        d["payload"] = op.payload
    if op.justification is not None:
        d["justification"] = op.justification
    return to_jsonable(d)


def variant_overrides(plan: VariantPlan) -> list[dict[str, Any]]:
    return [build_op_to_dict(op) for op in plan.build_ops]
