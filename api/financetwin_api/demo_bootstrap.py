"""One-click demo: company + twin + new_site run."""

from __future__ import annotations

from typing import Any

from financetwin_api.db import Store
from financetwin_api.packs_run import run_pack_for_company
from financetwin_api.orgs import set_company_org


DEMO_SNAPSHOT: dict[str, Any] = {
    "schema_version": "1.0",
    "company": {
        "currency": "EUR",
        "opening_cash": "80000",
        "default_purchase_payment_days": 0,
    },
    "fiscal": {
        "vat_rate": "0",
        "vat_settlement": "monthly",
        "vat_payment_lag_months": 0,
        "corp_tax_rate": "0",
        "corp_tax_payment_mode": "none",
    },
    "policies": {"min_cash": "10000"},
    "revenue_streams": [
        {
            "id": "R_demo",
            "name": "Ventas tienda",
            "revenue_type": "recurring",
            "start_year_month": "2027-01",
            "base_monthly_revenue": "25000",
            "gross_margin_pct": "0.45",
            "collection_days": 0,
        }
    ],
    "cost_items": [
        {
            "id": "C_demo",
            "name": "Opex base",
            "nature": "fixed",
            "start_year_month": "2027-01",
            "amount_monthly": "4000",
            "payment_days": 0,
        }
    ],
}

DEMO_INPUTS: dict[str, Any] = {
    "site_name": "Tienda demo",
    "open_year_month": "2027-01",
    "capex_total": "120000",
    "sales_run_rate": "35000",
    "gross_margin_pct": "0.40",
    "rent_monthly": "3500",
    "other_opex_monthly": "1200",
    "headcount": 2,
    "employer_cost_per_person": "2500",
    "debt_amount": "70000",
    "equity_amount": "50000",
    "loan_term_months": 60,
    "loan_annual_rate": "0.055",
    "horizon_months": 24,
    "discount_rate_annual": "0.08",
    "collection_days": 0,
}


def bootstrap_demo(store: Store, *, org_id: str | None = None) -> dict[str, Any]:
    company = store.create_company("Demo Tienda SL", "ES", "EUR")
    if org_id:
        set_company_org(store, company.id, org_id)
    mv_id = store.put_current_snapshot(company.id, DEMO_SNAPSHOT, label="demo-one-click")
    run = run_pack_for_company(
        store,
        company_id=company.id,
        pack_id="new_site",
        inputs=DEMO_INPUTS,
        variant="base",
    )
    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "country": company.country,
            "currency": company.currency,
            "created_at": company.created_at,
        },
        "model_version_id": mv_id,
        "snapshot": DEMO_SNAPSHOT,
        "inputs": DEMO_INPUTS,
        "run": run,
    }
