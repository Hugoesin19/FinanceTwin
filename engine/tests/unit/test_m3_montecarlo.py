"""M3 — Monte Carlo determinista (seed fija)."""

from __future__ import annotations

from financetwin_engine.analytics.montecarlo import run_montecarlo
from financetwin_engine.packs.new_site import NewSitePack
from financetwin_engine import snapshot_from_dict


def _snap():
    return snapshot_from_dict(
        {
            "schema_version": "1.0",
            "company": {
                "currency": "EUR",
                "opening_cash": "150000",
                "default_purchase_payment_days": 0,
            },
            "fiscal": {
                "vat_rate": "0",
                "vat_settlement": "monthly",
                "vat_payment_lag_months": 0,
                "corp_tax_rate": "0",
                "corp_tax_payment_mode": "none",
            },
            "policies": {"min_cash": "0"},
            "revenue_streams": [],
            "cost_items": [],
        }
    )


def _inputs():
    return {
        "site_name": "MC",
        "open_year_month": "2027-01",
        "capex_total": "100000",
        "sales_run_rate": "30000",
        "gross_margin_pct": "0.4",
        "rent_monthly": "2000",
        "debt_amount": "50000",
        "equity_amount": "50000",
        "loan_term_months": 48,
        "loan_annual_rate": "0.05",
        "horizon_months": 12,
        "discount_rate_annual": "0.08",
        "collection_days": 0,
    }


def test_montecarlo_seed_reproducible():
    pack = NewSitePack()
    snap = _snap()
    inputs = _inputs()
    a = run_montecarlo(
        pack=pack,
        snapshot=snap,
        base_inputs=inputs,
        n_sims=15,
        seed=7,
        ranges={"sales_run_rate": {"low": "0.9", "high": "1.1"}},
    )
    b = run_montecarlo(
        pack=pack,
        snapshot=snap,
        base_inputs=inputs,
        n_sims=15,
        seed=7,
        ranges={"sales_run_rate": {"low": "0.9", "high": "1.1"}},
    )
    assert a["n_completed"] > 0
    assert a["npv_p50"] == b["npv_p50"]
    assert "bajo los rangos" in a["disclaimer"].lower()
