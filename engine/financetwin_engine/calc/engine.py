"""Public engine entrypoint — MOTOR §6, §16."""

from __future__ import annotations

from decimal import Decimal

from financetwin_engine.calc.assets import build_asset_depreciation
from financetwin_engine.calc.capex import compute_capex_by_t
from financetwin_engine.calc.cash import build_cash_flow_series, compute_financing_need
from financetwin_engine.calc.decimal_money import D, money
from financetwin_engine.calc.loans import build_loan_schedule
from financetwin_engine.calc.metrics import calculate_investment_metrics
from financetwin_engine.calc.pnl import build_pnl_series
from financetwin_engine.model.calculation import (
    CalculationInput,
    CalculationResult,
    MonthlyBalance,
    PolicyCheck,
)
from financetwin_engine.trace.hashing import canonical_hash
from financetwin_engine.version import ENGINE_VERSION

ZERO = D(0)
ONE = D(1)

SIMPLIFICATIONS = (
    "vat_single_rate",
    "lag_floor_days_30",
    "tin_div_12",
    "equity_residual_balance",
    "opening_ar_ap_zero",
)


def _validate(inp: CalculationInput) -> list[str]:
    warnings: list[str] = []
    if inp.horizon_months < 1:
        raise ValueError("horizon_months must be >= 1")
    if inp.company.opening_cash is None:
        raise ValueError("opening_cash required")

    ids: list[str] = []
    for seq in (
        inp.revenue_streams,
        inp.cost_items,
        inp.payroll,
        inp.loans,
        inp.assets,
        inp.investments,
        inp.one_off_cash_events,
    ):
        for ent in seq:
            ids.append(ent.id)
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate entity ids")

    for loan in inp.loans:
        if loan.term_months < 1:
            raise ValueError(f"loan {loan.id}: term_months < 1")
        if isinstance(loan.principal, float):
            raise TypeError("float not allowed in loan.principal")

    for asset in inp.assets:
        if asset.useful_life_months < 1:
            raise ValueError(f"asset {asset.id}: useful_life_months < 1")

    vat = inp.company.fiscal.vat_rate
    corp = inp.company.fiscal.corp_tax_rate
    if vat < ZERO or vat > ONE:
        raise ValueError("vat_rate out of range [0, 1]")
    if corp < ZERO or corp > ONE:
        raise ValueError("corp_tax_rate out of range [0, 1]")

    if not inp.revenue_streams:
        warnings.append("no revenue streams")
    if inp.auto_finance_deficits:
        warnings.append("auto_finance_deficits not implemented in v0.1; ignored")

    for s in inp.revenue_streams:
        if s.collection_days > 180:
            warnings.append(f"stream {s.id}: collection_days > 180")

    warnings.extend(f"simplification:{name}" for name in SIMPLIFICATIONS)
    return warnings


def _vat_paid_series(
    pnl,
    vat_rate: Decimal,
    settlement: str,
    lag_months: int,
    horizon: int,
) -> list[Decimal]:
    """MOTOR §9.1 simplified: vat_net accrued; pay with lag (monthly)."""
    accrued = [money(p.revenue * vat_rate - (p.cogs + p.other_opex) * vat_rate) for p in pnl]
    paid = [ZERO] * horizon
    if settlement == "monthly":
        for t, amount in enumerate(accrued):
            pay_t = t + lag_months
            if 0 <= pay_t < horizon and amount > ZERO:
                paid[pay_t] = money(paid[pay_t] + amount)
    # quarterly: accumulate then pay — MVP minimal
    elif settlement == "quarterly":
        bucket = ZERO
        for t, amount in enumerate(accrued):
            bucket = money(bucket + amount)
            if (t + 1) % 3 == 0:
                pay_t = t + lag_months
                if bucket > ZERO and 0 <= pay_t < horizon:
                    paid[pay_t] = money(paid[pay_t] + bucket)
                bucket = ZERO
    return paid


def _build_balances(
    *,
    horizon: int,
    cash_flow,
    assets,
    loan_schedules: dict,
) -> tuple[MonthlyBalance, ...]:
    asset_nbv = [ZERO] * horizon
    for asset in assets:
        rows = build_asset_depreciation(asset, horizon)
        for row in rows:
            asset_nbv[row.t] = money(asset_nbv[row.t] + row.net_book_value)

    balances: list[MonthlyBalance] = []
    for t in range(horizon):
        cf = cash_flow[t]
        debt_total = ZERO
        debt_short = ZERO
        for sched in loan_schedules.values():
            if t < len(sched.rows):
                closing = sched.rows[t].closing_principal
                debt_total = money(debt_total + closing)
                # principal due in next 12 months
                remaining = ZERO
                for row in sched.rows[t + 1 : t + 13]:
                    remaining = money(remaining + row.principal_repaid)
                # short-term ≈ min(closing, sum of next 12 principal)
                short = money(min(closing, remaining)) if remaining > ZERO else ZERO
                if t == horizon - 1:
                    short = closing  # all remaining is "current" at end
                debt_short = money(debt_short + short)
        debt_long = money(debt_total - debt_short)
        if debt_long < ZERO:
            debt_long = ZERO
            debt_short = debt_total

        cash = cf.closing_cash
        ar = cf.accounts_receivable
        ap = cf.accounts_payable
        nca = asset_nbv[t]
        total_assets = money(nca + ar + cash)
        vat_pay = ZERO
        corp_pay = ZERO
        equity = money(total_assets - (debt_total + ap + vat_pay + corp_pay))
        total_le = money(debt_total + ap + vat_pay + corp_pay + equity)
        balances.append(
            MonthlyBalance(
                t=t,
                non_current_assets_net=nca,
                accounts_receivable=ar,
                cash=cash,
                total_assets=total_assets,
                debt_long_term=debt_long,
                debt_short_term=debt_short,
                accounts_payable=ap,
                vat_payable=vat_pay,
                corp_tax_payable=corp_pay,
                equity=equity,
                total_liabilities_equity=total_le,
            )
        )
    return tuple(balances)


def _policy_checks(inp: CalculationInput, financing_need, investment_metrics) -> tuple[PolicyCheck, ...]:
    checks: list[PolicyCheck] = []
    policy = inp.company.policies
    # min cash
    status = "pass"
    if financing_need.max_shortfall_vs_policy > ZERO:
        status = "fail"
    checks.append(
        PolicyCheck(
            policy_id="min_cash",
            status=status,
            message="cash vs policy minimum",
            value=financing_need.min_cash,
            threshold=policy.min_cash,
        )
    )
    if policy.max_payback_months is not None and investment_metrics is not None:
        pb = investment_metrics.payback_simple
        if pb is None:
            checks.append(
                PolicyCheck(
                    policy_id="max_payback_months",
                    status="fail",
                    message="payback beyond horizon",
                    value=None,
                    threshold=D(policy.max_payback_months),
                )
            )
        else:
            checks.append(
                PolicyCheck(
                    policy_id="max_payback_months",
                    status="pass" if pb <= policy.max_payback_months else "fail",
                    message="payback vs max",
                    value=D(pb),
                    threshold=D(policy.max_payback_months),
                )
            )
    if policy.min_irr is not None and investment_metrics is not None:
        irr = investment_metrics.irr_annual
        if irr is None:
            checks.append(
                PolicyCheck(
                    policy_id="min_irr",
                    status="fail",
                    message="IRR undefined",
                    threshold=policy.min_irr,
                )
            )
        else:
            checks.append(
                PolicyCheck(
                    policy_id="min_irr",
                    status="pass" if irr >= policy.min_irr else "fail",
                    message="IRR vs minimum",
                    value=irr,
                    threshold=policy.min_irr,
                )
            )
    return tuple(checks)


def _project_fcf(inp: CalculationInput, cash_flow, capex_by_t) -> list[Decimal]:
    """FCF before financing for investment metrics — MOTOR §10.1."""
    # MVP: operating_cash_flow - capex (exclude drawdowns / debt service already outside operating)
    return [
        money(cf.operating_cash_flow - cf.capex_paid)
        for cf in cash_flow
    ]


def calculate(inp: CalculationInput) -> CalculationResult:
    """Única entrada pública al motor — MOTOR §16."""
    warnings = _validate(inp)
    h = inp.horizon_months
    inputs_hash = canonical_hash(inp)

    # Loans
    loan_schedules = {
        loan.id: build_loan_schedule(loan, h) for loan in inp.loans
    }
    interest_by_t = [ZERO] * h
    for sched in loan_schedules.values():
        for row in sched.rows:
            if 0 <= row.t < h:
                interest_by_t[row.t] = money(interest_by_t[row.t] + row.interest_accrued)

    # P&L
    pnl = build_pnl_series(
        horizon=h,
        revenue_streams=inp.revenue_streams,
        cost_items=inp.cost_items,
        payroll=inp.payroll,
        assets=inp.assets,
        interest_expense_by_t=interest_by_t,
        corp_tax_rate=inp.company.fiscal.corp_tax_rate,
    )

    # CAPEX
    capex_by_t = compute_capex_by_t(
        horizon=h,
        investments=inp.investments,
        assets=inp.assets,
        one_offs=inp.one_off_cash_events,
    )

    vat_paid = _vat_paid_series(
        pnl,
        inp.company.fiscal.vat_rate,
        inp.company.fiscal.vat_settlement,
        inp.company.fiscal.vat_payment_lag_months,
        h,
    )

    # corp tax paid — MVP: none or annual_end last month sum of expenses
    corp_tax_paid = [ZERO] * h
    mode = inp.company.fiscal.corp_tax_payment_mode
    if mode == "annual_end":
        total_tax = money(sum((p.corp_tax_expense for p in pnl), ZERO))
        if total_tax > ZERO and h >= 1:
            corp_tax_paid[h - 1] = total_tax

    cash_flow = build_cash_flow_series(
        pnl=pnl,
        revenue_streams=inp.revenue_streams,
        cost_items=inp.cost_items,
        payroll=inp.payroll,
        opening_cash=inp.company.opening_cash,
        vat_rate=inp.company.fiscal.vat_rate,
        default_purchase_payment_days=inp.company.default_purchase_payment_days,
        loan_schedules=list(loan_schedules.values()),
        one_offs=inp.one_off_cash_events,
        capex_by_t=capex_by_t,
        corp_tax_paid_by_t=corp_tax_paid,
        vat_paid_by_t=vat_paid,
    )

    balance = _build_balances(
        horizon=h,
        cash_flow=cash_flow,
        assets=inp.assets,
        loan_schedules=loan_schedules,
    )

    fcf = _project_fcf(inp, cash_flow, capex_by_t)
    investment_metrics = None
    if any(fc != ZERO for fc in fcf):
        investment_metrics = calculate_investment_metrics(
            fcf, inp.discount_rate_annual
        )

    financing_need = compute_financing_need(
        cash_flow, policy_min_cash=inp.company.policies.min_cash
    )
    policy_checks = _policy_checks(inp, financing_need, investment_metrics)

    result_core = {
        "pnl": pnl,
        "cash_flow": cash_flow,
        "balance": balance,
        "loan_schedules": loan_schedules,
        "investment_metrics": investment_metrics,
        "financing_need": financing_need,
        "policy_checks": policy_checks,
    }
    result_hash = canonical_hash(result_core)

    return CalculationResult(
        engine_version=ENGINE_VERSION,
        inputs_hash=inputs_hash,
        result_hash=result_hash,
        horizon_months=h,
        pnl=pnl,
        cash_flow=cash_flow,
        balance=balance,
        loan_schedules=loan_schedules,
        investment_metrics=investment_metrics,
        financing_need=financing_need,
        policy_checks=policy_checks,
        warnings=tuple(warnings),
        simplifications_applied=SIMPLIFICATIONS,
    )
