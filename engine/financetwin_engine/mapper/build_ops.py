"""BuildOp application — MODELO §7.2 / DECISION_PACKS §2.4."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Literal, Sequence

from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper.snapshot import CompanyTwinSnapshot, snapshot_from_dict

EntityType = Literal[
    "revenue_streams",
    "cost_items",
    "payroll",
    "loans",
    "assets",
    "investments",
    "company",
    "fiscal",
    "policies",
    "assumptions",
    "one_off_cash_events",
    "business_units",
]

LIST_ENTITY_TYPES = {
    "revenue_streams",
    "cost_items",
    "payroll",
    "loans",
    "assets",
    "investments",
    "assumptions",
    "one_off_cash_events",
    "business_units",
}

_MONEY_FIELDS = {
    "opening_cash",
    "vat_rate",
    "corp_tax_rate",
    "min_cash",
    "max_debt_ebitda",
    "min_dscr",
    "min_irr",
    "max_capex_pct_cash",
    "base_monthly_revenue",
    "gross_margin_pct",
    "amount_monthly",
    "pct_of_revenue",
    "principal",
    "annual_interest_rate",
    "acquisition_cost",
    "residual_value",
    "monthly_employer_cost",
    "origination_fee",
    "own_funds_amount",
    "growth_annual",
    "amount",
}


@dataclass(frozen=True)
class BuildOp:
    op: Literal["add_entity", "set_field"]
    entity_type: EntityType
    entity_id: str | None = None
    field: str | None = None
    value: Any = None
    payload: dict[str, Any] | None = None
    justification: str | None = None


class BuildOpError(ValueError):
    pass


def _entity_from_payload(entity_type: str, payload: dict[str, Any]) -> Any:
    temp: dict[str, Any] = {
        "schema_version": "1.0",
        "company": {"currency": "EUR", "opening_cash": "0"},
        entity_type: [payload],
    }
    snap = snapshot_from_dict(temp, validate=False)
    items = getattr(snap, entity_type)
    if not items:
        raise BuildOpError(f"failed to parse add_entity payload for {entity_type}")
    return items[0]


def _coerce_money(value: Any) -> str:
    if isinstance(value, float):
        raise TypeError("float not allowed in BuildOp value")
    return str(D(value))


def _normalize(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    return obj


def apply_build_ops(
    snapshot: CompanyTwinSnapshot,
    overrides: Sequence[BuildOp],
) -> CompanyTwinSnapshot:
    """effective_snapshot = apply_build_ops(base, overrides). Does not mutate input."""
    data = _normalize(asdict(snapshot))

    adds: list[BuildOp] = []
    sets: list[BuildOp] = []
    for op in overrides:
        kind = op.op or "set_field"
        if kind == "add_entity":
            adds.append(op)
        elif kind == "set_field":
            sets.append(op)
        else:
            raise BuildOpError(f"unsupported op: {kind}")

    for op in adds:
        if op.entity_type not in LIST_ENTITY_TYPES:
            raise BuildOpError(f"add_entity not allowed on {op.entity_type}")
        if not op.payload:
            raise BuildOpError("add_entity requires payload")
        entity = _entity_from_payload(op.entity_type, op.payload)
        if op.entity_id and getattr(entity, "id") != op.entity_id:
            raise BuildOpError("add_entity entity_id must match payload.id")
        data[op.entity_type] = list(data.get(op.entity_type) or [])
        data[op.entity_type].append(_normalize(asdict(entity)))

    for op in sets:
        if op.field is None:
            raise BuildOpError("set_field requires field")
        if op.entity_type in ("company", "fiscal", "policies"):
            block = data[op.entity_type]
            if op.field in _MONEY_FIELDS:
                block[op.field] = _coerce_money(op.value)
            else:
                block[op.field] = op.value
            continue

        if op.entity_type not in LIST_ENTITY_TYPES:
            raise BuildOpError(f"set_field unsupported entity_type {op.entity_type}")
        if not op.entity_id:
            raise BuildOpError("set_field requires entity_id")
        found = False
        for item in data[op.entity_type]:
            if item["id"] == op.entity_id:
                if op.field in _MONEY_FIELDS:
                    item[op.field] = _coerce_money(op.value)
                else:
                    item[op.field] = op.value
                found = True
                break
        if not found:
            raise BuildOpError(
                f"set_field: entity {op.entity_id} not found in {op.entity_type}"
            )

    return snapshot_from_dict(data)
