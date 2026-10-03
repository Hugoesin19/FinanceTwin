"""One-off cash events — MOTOR §4.1."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

OneOffKind = Literal[
    "equity_injection",
    "dividend",
    "other_in",
    "other_out",
    "capex",
]


@dataclass(frozen=True)
class OneOffCashEvent:
    id: str
    t: int
    amount: Decimal
    kind: OneOffKind
