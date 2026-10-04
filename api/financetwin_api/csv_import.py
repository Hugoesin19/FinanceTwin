"""Parse plantilla CSV → CompanyTwinSnapshot dict (P5)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from financetwin_engine import snapshot_from_dict
from financetwin_engine.mapper.snapshot import SnapshotValidationError

SECTION_RE = re.compile(r"^#\s*SECTION\s+([A-Za-z0-9_]+)\s*$", re.IGNORECASE)

REQUIRED_SECTIONS = ("company", "fiscal", "policies")

LIST_SECTIONS = {
    "revenue_streams",
    "cost_items",
    "payroll",
    "loans",
}


class TwinCsvError(ValueError):
    """Error de formato CSV (antes de validar el snapshot)."""


def _blank(v: str | None) -> bool:
    return v is None or str(v).strip() == ""


def _clean_row(row: dict[str, str | None]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        if k is None or _blank(k):
            continue
        key = k.strip()
        if _blank(v):
            continue
        val = str(v).strip()
        if key == "is_vatable":
            out[key] = val.lower() in ("1", "true", "yes", "y", "si", "sí")
        elif key in (
            "collection_days",
            "payment_days",
            "default_purchase_payment_days",
            "vat_payment_lag_months",
            "headcount",
            "term_months",
            "grace_months",
            "max_payback_months",
        ):
            out[key] = int(val)
        else:
            out[key] = val
    return out


def _split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip("\n\r")
        m = SECTION_RE.match(line.strip())
        if m:
            if current is not None:
                sections[current] = buf
            current = m.group(1).lower()
            buf = []
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current is None:
            raise TwinCsvError(
                "CSV must start with a # SECTION header (see templates/README.md)"
            )
        buf.append(line)
    if current is not None:
        sections[current] = buf
    return sections


def _parse_table(lines: list[str]) -> list[dict[str, Any]]:
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    if not reader.fieldnames:
        raise TwinCsvError("section table missing header row")
    rows: list[dict[str, Any]] = []
    for row in reader:
        cleaned = _clean_row(row)
        if cleaned:
            rows.append(cleaned)
    return rows


def parse_twin_csv(text: str) -> dict[str, Any]:
    """Convierte texto CSV de plantilla en dict snapshot (sin validar aún)."""
    if text is None or not str(text).strip():
        raise TwinCsvError("empty CSV")
    # strip UTF-8 BOM
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    if not text.strip():
        raise TwinCsvError("empty CSV")
    sections = _split_sections(text)
    missing = [s for s in REQUIRED_SECTIONS if s not in sections]
    if missing:
        raise TwinCsvError(f"missing required sections: {missing}")

    company_rows = _parse_table(sections["company"])
    fiscal_rows = _parse_table(sections["fiscal"])
    policy_rows = _parse_table(sections["policies"])
    if len(company_rows) != 1:
        raise TwinCsvError("section company must have exactly 1 data row")
    if len(fiscal_rows) != 1:
        raise TwinCsvError("section fiscal must have exactly 1 data row")
    if len(policy_rows) != 1:
        raise TwinCsvError("section policies must have exactly 1 data row")

    snapshot: dict[str, Any] = {
        "schema_version": "1.0",
        "company": company_rows[0],
        "fiscal": fiscal_rows[0],
        "policies": policy_rows[0],
    }

    for name in LIST_SECTIONS:
        if name not in sections:
            continue
        rows = _parse_table(sections[name])
        if rows:
            snapshot[name] = rows

    unknown = set(sections) - set(REQUIRED_SECTIONS) - LIST_SECTIONS
    if unknown:
        raise TwinCsvError(f"unknown sections: {sorted(unknown)}")

    return snapshot


def parse_and_validate_twin_csv(text: str) -> dict[str, Any]:
    """Parse + `snapshot_from_dict` (errores de schema → SnapshotValidationError)."""
    raw = parse_twin_csv(text)
    snapshot_from_dict(raw, validate=True)
    return raw


def format_import_error(exc: BaseException) -> dict[str, Any] | str:
    if isinstance(exc, TwinCsvError):
        return {"code": "csv_format", "message": str(exc)}
    if isinstance(exc, SnapshotValidationError):
        return {"code": "snapshot_invalid", "message": str(exc)}
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return {"code": "snapshot_invalid", "message": str(exc)}
    return {"code": "import_error", "message": str(exc)}
