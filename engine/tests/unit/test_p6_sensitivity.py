"""P6 — sensibilidad / inversa / stress (new_site analysis_plan)."""

from __future__ import annotations

from decimal import Decimal

from financetwin_engine import NewSitePack, run_analysis, snapshot_from_dict


def _twin():
    return snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {"currency": "EUR", "opening_cash": "100000"},
            "fiscal": {
                "vat_rate": "0",
                "vat_settlement": "monthly",
                "vat_payment_lag_months": 0,
                "corp_tax_rate": "0",
                "corp_tax_payment_mode": "none",
            },
            "policies": {"min_cash": "0"},
        }
    )


def _inputs(**over):
    data = {
        "site_name": "Tienda Sens",
        "open_year_month": "2027-01",
        "capex_total": "100000",
        "sales_run_rate": "25000",
        "gross_margin_pct": "0.40",
        "rent_monthly": "2000",
        "other_opex_monthly": "500",
        "debt_amount": "60000",
        "equity_amount": "40000",
        "loan_term_months": 60,
        "loan_annual_rate": "0.06",
        "horizon_months": 24,
        "discount_rate_annual": "0.08",
        "collection_days": 0,
        "sales_ramp_months": 6,
    }
    data.update(over)
    return data


def test_run_analysis_direct_inverse_stress() -> None:
    pack = NewSitePack()
    snap = _twin()
    out = run_analysis(pack, snap, _inputs(), include=("direct", "inverse", "stress"))
    assert out["pack_id"] == "new_site"
    assert out["direct"]["base"]["npv"] is not None
    assert isinstance(out["direct"]["base"]["npv"], str)
    assert any(
        r.get("variable") == "sales_run_rate" and not r.get("skipped")
        for r in out["direct"]["rows"]
    )
    sales_rows = [
        r
        for r in out["direct"]["rows"]
        if r.get("variable") == "sales_run_rate" and not r.get("skipped")
    ]
    assert len(sales_rows) == 2
    npvs = [Decimal(r["metrics"]["npv"]) for r in sales_rows]
    assert npvs[0] != npvs[1]

    inv = out["inverse"]["rows"]
    assert inv
    sales_npv = next(
        r
        for r in inv
        if r.get("variable") == "sales_run_rate" and r.get("metric") == "npv"
    )
    assert "found" in sales_npv

    stress = out["stress"]["rows"]
    assert {r["stress"] for r in stress} >= {
        "sales_-15pct",
        "sales_-30pct",
        "open_plus_2m",
        "rate_plus_200bp",
    }
    assert all("metrics" in r or r.get("skipped") for r in stress)


def test_direct_no_float_in_payload() -> None:
    out = run_analysis(NewSitePack(), _twin(), _inputs(), include=("direct",))

    def walk(o):
        if isinstance(o, float):
            raise AssertionError(f"float found: {o}")
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(out)
