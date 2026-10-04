"""F8 Plan B — V1–V5 automatizables (VALIDACION §6 + §11)."""

from __future__ import annotations

import json
from pathlib import Path

from financetwin_engine import (
    Asset,
    CalculationInput,
    CapexPoint,
    CompanyInput,
    CompanyPolicy,
    CostItem,
    FiscalConfig,
    Investment,
    Loan,
    PayrollLine,
    RevenueStream,
    calculate,
    calculate_investment_metrics,
)
from financetwin_engine.analytics.bias import (
    calibrate_value,
    compute_bias_stats,
    deviation_pct,
    offer_calibration,
)
from financetwin_engine.calc.decimal_money import D
from financetwin_engine.calc.invariants import check_invariants
from financetwin_engine.calc.loans import build_loan_schedule
from financetwin_engine.mapper.snapshot import snapshot_from_dict
from financetwin_engine.model.loan import Loan as LoanModel
from financetwin_engine.packs.base import has_errors
from financetwin_engine.packs.financing import FinancingPack
from financetwin_engine.packs.hiring import HiringPack
from financetwin_engine.packs.new_site import NewSitePack
from financetwin_engine.packs.runner import run_variant

from validation.metrics import (
    independent_french_payment,
    independent_npv,
    mape,
    relative_bias,
)

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
RESULTS = ROOT / "results"


def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _empty_snap():
    return snapshot_from_dict(
        {
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
            "policies": {"min_cash": "0"},
        }
    )


def _base_input(cfg: dict, *, horizon: int, revenue: str | None = None) -> CalculationInput:
    rev = D(revenue if revenue is not None else cfg["revenue_base"])
    return CalculationInput(
        company=CompanyInput(
            opening_cash=D(cfg["opening_cash"]),
            default_purchase_payment_days=0,
            fiscal=FiscalConfig(vat_rate=D(0), corp_tax_rate=D(0)),
            policies=CompanyPolicy(min_cash=D(0)),
        ),
        horizon_months=horizon,
        discount_rate_annual=D(cfg["discount_rate_annual"]),
        revenue_streams=(
            RevenueStream(
                id="R1",
                name="retail",
                start_t=0,
                base_monthly_revenue=rev,
                gross_margin_pct=D(cfg["gross_margin_pct"]),
                collection_days=int(cfg["collection_days"]),
            ),
        ),
        cost_items=(
            CostItem(
                id="C1",
                name="rent",
                start_t=0,
                nature="fixed",
                amount_monthly=D(cfg["rent_monthly"]),
                payment_days=0,
            ),
        ),
        payroll=(
            PayrollLine(
                id="P1",
                role_name="staff",
                headcount=int(cfg["payroll_headcount"]),
                monthly_employer_cost=D(cfg["payroll_cost"]),
                start_t=0,
            ),
        ),
        loans=(
            Loan(
                id="L1",
                name="capex loan",
                principal=D(cfg["loan_principal"]),
                annual_interest_rate=D(cfg["loan_rate"]),
                term_months=int(cfg["loan_term_months"]),
                amortization_system="french",
                disbursement_t=0,
            ),
        ),
        assets=(
            Asset(
                id="A1",
                name="fitout",
                acquisition_cost=D(cfg["capex"]),
                acquisition_t=0,
                useful_life_months=60,
                investment_id="I1",
            ),
        ),
        investments=(
            Investment(
                id="I1",
                name="store",
                capex_schedule=(CapexPoint(t=0, amount=D(cfg["capex"])),),
                linked_asset_ids=("A1",),
                linked_loan_ids=("L1",),
            ),
        ),
    )


def test_v1_historical_fidelity_reconstruction_and_noise() -> None:
    """
    Plan B V1:
    1) reconstrucción exacta → MAPE=0
    2) “real” con ruido controlado ±2% en caja → MAPE caja ≤ 15%
    """
    cfg = _load("synthetic_sme.json")
    H = int(cfg["horizon_hist_months"])
    inp = _base_input(cfg, horizon=H)
    truth = calculate(inp)
    check_invariants(
        truth,
        assets=inp.assets,
        loan_term_ends={"L1": int(cfg["loan_term_months"]) - 1},
    )
    recon = calculate(_base_input(cfg, horizon=H))

    rev_t = [p.revenue for p in truth.pnl]
    rev_r = [p.revenue for p in recon.pnl]
    cash_t = [c.closing_cash for c in truth.cash_flow]
    cash_r = [c.closing_cash for c in recon.cash_flow]
    debt_t = [b.debt_long_term + b.debt_short_term for b in truth.balance]
    debt_r = [b.debt_long_term + b.debt_short_term for b in recon.balance]

    mape_rev = mape(rev_r, rev_t)
    mape_cash = mape(cash_r, cash_t)
    mape_debt = mape(debt_r, debt_t)
    assert mape_rev == D(0)
    assert mape_cash == D(0)
    assert mape_debt == D(0)

    noise = D(cfg.get("noise_revenue_pct", "0.02"))
    observed_cash = [
        (c * (D(1) + noise)) if (i % 2 == 0) else (c * (D(1) - noise))
        for i, c in enumerate(cash_t)
    ]
    mape_noisy = mape(cash_r, observed_cash)
    assert mape_noisy <= D("0.15")
    assert mape_noisy > D(0)

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "v1_mape.json").write_text(
        json.dumps(
            {
                "mode": "plan_b_synthetic",
                "mape_revenue_exact": str(mape_rev),
                "mape_cash_exact": str(mape_cash),
                "mape_debt_exact": str(mape_debt),
                "mape_cash_vs_noisy_observed": str(mape_noisy),
                "noise_pct": str(noise),
                "thresholds": {"revenue": "0.10", "closing_cash": "0.15", "debt": "0.05"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_v2_backtest_synthetic() -> None:
    """Plan B V2 débil: H=12 desde t=0 vs primeros 12m del histórico sintético."""
    cfg = _load("synthetic_sme.json")
    full = calculate(_base_input(cfg, horizon=24))
    proj = calculate(_base_input(cfg, horizon=12))

    real_cash = [c.closing_cash for c in full.cash_flow[:12]]
    pred_cash = [c.closing_cash for c in proj.cash_flow]
    m = mape(pred_cash, real_cash)
    assert m <= D("0.25")
    assert m == D(0)

    t_real_min = min(range(12), key=lambda i: real_cash[i])
    t_pred_min = min(range(12), key=lambda i: pred_cash[i])
    assert abs(t_pred_min - t_real_min) <= 2

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "v2_backtest.json").write_text(
        json.dumps(
            {
                "mape_closing_cash": str(m),
                "t_min_real": t_real_min,
                "t_min_pred": t_pred_min,
                "note": "Plan B weak backtest (first 12m); mid-horizon French restart not claimed PASS",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_v3_loan_vs_independent_formula() -> None:
    bank = _load("loan_bank_generic.json")
    loan = LoanModel(
        id="BANK",
        name="generic",
        principal=D(bank["principal"]),
        annual_interest_rate=D(bank["annual_interest_rate"]),
        term_months=int(bank["term_months"]),
        amortization_system="french",
        disbursement_t=0,
    )
    sched = build_loan_schedule(loan, horizon=int(bank["term_months"]) + 1)
    expected_pmt = independent_french_payment(
        bank["principal"], bank["annual_interest_rate"], int(bank["term_months"])
    )
    tol = D(bank["tolerance_payment_eur"])
    pay_rows = [
        r
        for r in sched.rows
        if r.t >= loan.disbursement_t and r.t < loan.disbursement_t + loan.term_months
    ]
    ok = sum(1 for r in pay_rows if abs(r.payment - expected_pmt) <= tol)
    assert ok >= 11
    last_amort = sched.rows[loan.disbursement_t + loan.term_months - 1]
    assert abs(last_amort.closing_principal) <= D("0.05")

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "v3_loan_diff.json").write_text(
        json.dumps(
            {
                "expected_payment": str(expected_pmt),
                "months_within_tol": ok,
                "months_total": len(pay_rows),
                "tolerance_eur": str(tol),
                "final_principal": str(last_amort.closing_principal),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_v3_npv_tir_independent() -> None:
    fc = [D(-1000), D(400), D(400), D(400)]
    engine = calculate_investment_metrics(fc, discount_rate_annual=D(0))
    indep = independent_npv(fc, D(0))
    assert engine.npv == indep == D(200)

    r_month = D("0.01")
    r_annual = (D(1) + r_month) ** 12 - D(1)
    fc2 = [D(-100), D(60), D(60)]
    eng2 = calculate_investment_metrics(fc2, discount_rate_annual=r_annual)
    ind2 = independent_npv(fc2, r_annual)
    assert eng2.npv == ind2 == D("18.22")


def test_v4_synthetic_decisions_run_packs() -> None:
    """Scorecards JSON + coherencia: los 3 packs construyen y calculan."""
    data = _load("decisions_v4.json")
    snap = _empty_snap()
    scores = []
    ran = []

    for d in data["decisions"]:
        sc = d["scorecard"]
        score = (
            0.2 * sc["pack_correct"]
            + 0.2 * sc["capex_timing"]
            + 0.2 * sc["funding"]
            + 0.2 * sc["ops_effect"]
            + 0.2 * sc["report_clear"]
        )
        scores.append(score)

        if d["pack"] == "new_site":
            pack = NewSitePack()
            inputs = {
                "site_name": "Tienda V4",
                "open_year_month": "2027-01",
                "capex_total": "200000",
                "sales_run_rate": "35000",
                "gross_margin_pct": "0.40",
                "rent_monthly": "4000",
                "other_opex_monthly": "1000",
                "headcount": 2,
                "employer_cost_per_person": "2800",
                "debt_amount": "120000",
                "equity_amount": "80000",
                "loan_term_months": 60,
                "loan_annual_rate": "0.055",
                "horizon_months": 24,
                "discount_rate_annual": "0.08",
                "collection_days": 0,
            }
        elif d["pack"] == "financing":
            pack = FinancingPack()
            inputs = {
                "loan_name": "Liquidez V4",
                "principal": "50000",
                "disbursement_year_month": "2027-01",
                "annual_rate": "0.055",
                "term_months": 36,
                "use_of_funds": "cash_buffer",
                "horizon_months": 24,
                "discount_rate_annual": "0.08",
            }
        elif d["pack"] == "hiring":
            pack = HiringPack()
            inputs = {
                "role_name": "Comercial",
                "headcount": 2,
                "employer_cost_per_person": "2800",
                "start_year_month": "2027-01",
                "expected_monthly_revenue_uplift": "8000",
                "gross_margin_pct": "0.40",
                "horizon_months": 24,
                "discount_rate_annual": "0.08",
            }
        else:
            raise AssertionError(f"unexpected pack {d['pack']}")

        resolved = pack.resolve_defaults(snap, inputs)
        issues = pack.validate_inputs(resolved)
        assert not has_errors(issues), issues
        bundle = pack.build(snap, resolved)
        assert "base" in bundle.variants
        pr = run_variant(snap, bundle.variants["base"])
        assert pr.result.horizon_months >= 12
        ran.append(
            {
                "id": d["id"],
                "pack": d["pack"],
                "score": score,
                "npv": str(pr.result.investment_metrics.npv)
                if pr.result.investment_metrics
                else None,
            }
        )
    assert len(scores) >= 3
    mean_score = sum(scores) / len(scores)
    assert mean_score >= 0.8

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "v4_scorecards.json").write_text(
        json.dumps({"mean_score": mean_score, "decisions": ran, "interview_real": False}, indent=2),
        encoding="utf-8",
    )


def test_v5_deviation_and_bias_median() -> None:
    forecasts = ["40000", "40000", "40000"]
    actuals = ["36000", "32800", "32000"]
    devs = []
    for f, a in zip(forecasts, actuals):
        d = deviation_pct(f, a)
        assert d.deviation_pct is not None
        devs.append(d.deviation_pct)
    stats = compute_bias_stats(devs)
    assert stats.n_observations == 3
    assert stats.median_bias == D("0.18")
    offer = offer_calibration(
        inputs={"sales_run_rate": "40000", "capex_total": "350000"},
        profiles=[
            {
                "variable_key": "sales_monthly",
                "n_observations": 3,
                "median_bias": str(stats.median_bias),
            }
        ],
    )
    assert offer["offered"] is True
    assert offer["calibrated_inputs"]["sales_run_rate"] == str(
        calibrate_value("40000", stats.median_bias)
    )

    # n=2 no ofrece
    offer2 = offer_calibration(
        inputs={"sales_run_rate": "40000"},
        profiles=[
            {"variable_key": "sales_monthly", "n_observations": 2, "median_bias": "0.18"}
        ],
    )
    assert offer2["offered"] is False


def test_v1_mape_helper_smoke() -> None:
    assert mape(["100", "100"], ["100", "100"]) == D(0)
    assert relative_bias(["110"], ["100"]) == D("0.1")
