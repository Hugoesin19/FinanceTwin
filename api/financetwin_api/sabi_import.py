"""Import Excel/SABI PGC 2007 → twin snapshot draft (human confirm before PUT)."""

from __future__ import annotations

import csv
import io
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from financetwin_engine.calc.decimal_money import D

ZERO = D(0)


class SabiImportError(ValueError):
    """Formato / mapeo SABI inválido."""


def _norm(label: str) -> str:
    s = str(label).strip().lower()
    s = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    s = re.sub(r"\s+", " ", s)
    return s


def _to_dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, (int, float, Decimal)):
        try:
            return D(str(v))
        except (InvalidOperation, ValueError):
            return None
    s = str(v).strip().replace(" ", "").replace(",", ".")
    if not s or s.lower() in ("n.d.", "nd", "-", "—"):
        return None
    try:
        return D(s)
    except (InvalidOperation, ValueError):
        return None


def _abs_money(v: Decimal | None) -> Decimal:
    if v is None:
        return ZERO
    return abs(v)


# Label substrings → map keys (first match wins per priority order)
_MAP_RULES: list[tuple[str, str]] = [
    ("vii efectivo y otros activos liquidos equivalentes", "cash"),
    ("1. tesoreria", "cash"),
    ("importe neto de la cifra de negocios", "revenue_annual"),
    ("4. aprovisionamientos", "cogs_annual"),
    ("6. gastos de personal", "payroll_annual"),
    ("7. otros gastos de explotacion", "opex_annual"),
    ("2. deudas con entidades de credito", "bank_debt"),  # may hit LP then CP
]


def _match_key(label: str) -> str | None:
    n = _norm(label)
    for needle, key in _MAP_RULES:
        if needle in n:
            return key
    return None


def parse_sabi_rows(
    rows: list[tuple[Any, ...]],
    *,
    company_name: str | None = None,
    year_month: str = "2025-01",
) -> dict[str, Any]:
    """
    rows: iterable of (label, value, ...) — value typically col C (index 2) in SABI export.
    Returns draft with mapping preview + proposed snapshot.
    """
    found: dict[str, Decimal] = {}
    mapping: list[dict[str, Any]] = []
    bank_debt_total = ZERO
    name = company_name or "Empresa SABI"

    for row in rows:
        if not row:
            continue
        label = row[0]
        if label is None:
            continue
        # Prefer column C (index 2); fall back to index 1
        val = None
        if len(row) > 2:
            val = _to_dec(row[2])
        if val is None and len(row) > 1:
            val = _to_dec(row[1])
        key = _match_key(str(label))
        if key is None or val is None:
            continue
        if key == "bank_debt":
            bank_debt_total += _abs_money(val)
            mapping.append(
                {
                    "source_label": str(label).strip(),
                    "maps_to": "bank_debt_hint",
                    "raw_value": str(val),
                    "note": "Suma deudas con entidades de crédito (LP+CP) como hint",
                }
            )
            continue
        # Prefer first non-zero / keep first for cash (VII then Tesorería — take first cash)
        if key in found and key != "cash":
            continue
        if key == "cash" and key in found:
            # Prefer more specific Tesorería if already have VII
            if "tesorer" in _norm(str(label)):
                found[key] = _abs_money(val)
                mapping.append(
                    {
                        "source_label": str(label).strip(),
                        "maps_to": key,
                        "raw_value": str(val),
                        "note": "Tesorería (preferida)",
                    }
                )
            continue
        found[key] = _abs_money(val)
        mapping.append(
            {
                "source_label": str(label).strip(),
                "maps_to": key,
                "raw_value": str(val),
                "note": _note_for(key),
            }
        )

    if bank_debt_total > ZERO:
        found["bank_debt"] = bank_debt_total

    cash = found.get("cash", ZERO)
    rev_m = (found.get("revenue_annual", ZERO) / D(12)) if found.get("revenue_annual") else ZERO
    cogs_m = (found.get("cogs_annual", ZERO) / D(12)) if found.get("cogs_annual") else ZERO
    pay_m = (found.get("payroll_annual", ZERO) / D(12)) if found.get("payroll_annual") else ZERO
    opex_m = (found.get("opex_annual", ZERO) / D(12)) if found.get("opex_annual") else ZERO
    costs_m = cogs_m + pay_m + opex_m
    margin = ZERO
    if rev_m > ZERO and cogs_m >= ZERO:
        margin = max(ZERO, min(D(1), (rev_m - cogs_m) / rev_m))

    snapshot: dict[str, Any] = {
        "schema_version": "1.0",
        "company": {
            "currency": "EUR",
            "opening_cash": str(cash),
            "default_purchase_payment_days": 30,
        },
        "fiscal": {
            "vat_rate": "0.21",
            "vat_settlement": "monthly",
            "vat_payment_lag_months": 1,
            "corp_tax_rate": "0.25",
            "corp_tax_payment_mode": "none",
        },
        "policies": {"min_cash": "0"},
        "revenue_streams": [],
        "cost_items": [],
        "payroll": [],
        "loans": [],
    }
    if rev_m > ZERO:
        snapshot["revenue_streams"].append(
            {
                "id": "R_SABI",
                "name": "Cifra de negocios / 12",
                "revenue_type": "recurring",
                "start_year_month": year_month,
                "base_monthly_revenue": str(money_str(rev_m)),
                "gross_margin_pct": str(money_str(margin)) if margin > ZERO else "0.3",
                "collection_days": 30,
            }
        )
    if costs_m > ZERO:
        snapshot["cost_items"].append(
            {
                "id": "C_SABI",
                "name": "Costes explotacion / 12",
                "nature": "fixed",
                "start_year_month": year_month,
                "amount_monthly": str(money_str(costs_m)),
                "payment_days": 30,
            }
        )

    return {
        "company_name_hint": name,
        "year_month": year_month,
        "mapping": mapping,
        "derived": {
            "opening_cash": str(cash),
            "revenue_monthly": str(money_str(rev_m)),
            "costs_monthly": str(money_str(costs_m)),
            "gross_margin_pct": str(money_str(margin)) if margin > ZERO else None,
            "bank_debt_hint": str(found["bank_debt"]) if "bank_debt" in found else None,
        },
        "snapshot": snapshot,
        "confirm_required": True,
        "notes": [
            "Importación heurística PGC 2007 (SABI). Revisa el mapeo antes de confirmar.",
            "Cifras anuales se dividen entre 12 para run-rate mensual.",
            "Deuda bancaria es solo hint; no crea préstamo automáticamente.",
        ],
    }


def money_str(v: Decimal) -> str:
    return format(v.quantize(D("0.01")), "f")


def _note_for(key: str) -> str:
    return {
        "cash": "→ caja inicial",
        "revenue_annual": "→ ingresos mensuales (/12)",
        "cogs_annual": "→ parte de costes (/12)",
        "payroll_annual": "→ parte de costes (/12)",
        "opex_annual": "→ parte de costes (/12)",
    }.get(key, key)


def parse_sabi_csv_text(text: str, **kwargs: Any) -> dict[str, Any]:
    reader = csv.reader(io.StringIO(text))
    rows = [tuple(r) for r in reader]
    name = kwargs.pop("company_name", None)
    if rows and rows[0] and rows[0][0] and not _match_key(str(rows[0][0])):
        # first cell might be company name
        if name is None and len(str(rows[0][0])) < 120:
            name = str(rows[0][0]).strip()
    return parse_sabi_rows(rows, company_name=name, **kwargs)


def parse_sabi_xlsx_bytes(data: bytes, **kwargs: Any) -> dict[str, Any]:
    try:
        import openpyxl
    except ImportError as e:
        raise SabiImportError(
            "openpyxl no está instalado; exporta a CSV o instala openpyxl"
        ) from e
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows: list[tuple[Any, ...]] = []
    name = kwargs.get("company_name")
    for i, row in enumerate(ws.iter_rows(max_col=6, values_only=True)):
        if i == 0 and name is None and row and row[1]:
            name = str(row[1]).strip()
        elif i == 0 and name is None and row and row[0]:
            name = str(row[0]).strip()
        rows.append(tuple(row))
    wb.close()
    return parse_sabi_rows(rows, company_name=name, year_month=kwargs.get("year_month", "2025-01"))
