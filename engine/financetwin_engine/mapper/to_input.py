"""Snapshot → CalculationInput — MODELO §11."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from financetwin_engine.calc.decimal_money import D
from financetwin_engine.mapper.build_ops import BuildOp, apply_build_ops
from financetwin_engine.mapper.snapshot import (
    CompanyTwinSnapshot,
    SnapshotValidationError,
    validate_snapshot,
)
from financetwin_engine.mapper.time import months_between
from financetwin_engine.model.asset import Asset
from financetwin_engine.model.calculation import CalculationInput
from financetwin_engine.model.company import (
    CompanyInput,
    CompanyPolicy,
    FiscalConfig,
)
from financetwin_engine.model.costs import CostItem, PayrollLine
from financetwin_engine.model.investment import CapexPoint, Investment
from financetwin_engine.model.loan import Loan
from financetwin_engine.model.one_off import OneOffCashEvent
from financetwin_engine.model.revenue import RevenueStream
from financetwin_engine.trace.hashing import canonical_hash

ZERO = D(0)


@dataclass(frozen=True)
class ScenarioSpec:
    """Campos de Scenario necesarios para el mapper (MODELO §7.1)."""

    anchor_year_month: str
    horizon_months: int
    discount_rate_annual: Decimal
    auto_finance_deficits: bool = False
    overrides: tuple[BuildOp, ...] = ()


@dataclass(frozen=True)
class MappedCalculation:
    calculation_input: CalculationInput
    inputs_hash: str
    effective_snapshot: CompanyTwinSnapshot


def _window_t(
    anchor: str,
    start_ym: str,
    end_ym: str | None,
    horizon: int,
) -> tuple[int, int | None] | None:
    """
    Returns (start_t, end_t) or None if excluded.
    MODELO §11.2 step 5.
    """
    start_t = months_between(anchor, start_ym)
    end_t = months_between(anchor, end_ym) if end_ym else None

    if end_t is not None and end_t < 0:
        return None  # ended before anchor
    if start_t < 0:
        # still active at anchor → start_t = 0
        start_t = 0
    if start_t >= horizon:
        return None
    if end_t is not None and end_t >= horizon:
        end_t = horizon - 1
    return start_t, end_t


def to_calculation_input(
    snapshot: CompanyTwinSnapshot,
    scenario: ScenarioSpec,
) -> MappedCalculation:
    validate_snapshot(snapshot)
    if scenario.horizon_months < 1:
        raise ValueError("horizon_months must be >= 1")

    effective = apply_build_ops(snapshot, scenario.overrides)
    validate_snapshot(effective)

    anchor = scenario.anchor_year_month
    h = scenario.horizon_months

    company = CompanyInput(
        currency=effective.company.currency,
        opening_cash=effective.company.opening_cash,
        default_purchase_payment_days=effective.company.default_purchase_payment_days,
        fiscal=FiscalConfig(
            vat_rate=effective.fiscal.vat_rate,
            vat_settlement=effective.fiscal.vat_settlement,
            vat_payment_lag_months=effective.fiscal.vat_payment_lag_months,
            corp_tax_rate=effective.fiscal.corp_tax_rate,
            corp_tax_payment_mode=effective.fiscal.corp_tax_payment_mode,
        ),
        policies=CompanyPolicy(
            min_cash=effective.policies.min_cash,
            max_debt_ebitda=effective.policies.max_debt_ebitda,
            min_dscr=effective.policies.min_dscr,
            max_payback_months=effective.policies.max_payback_months,
            min_irr=effective.policies.min_irr,
            max_capex_pct_cash=effective.policies.max_capex_pct_cash,
        ),
    )

    revenue_streams: list[RevenueStream] = []
    for s in effective.revenue_streams:
        win = _window_t(anchor, s.start_year_month, s.end_year_month, h)
        if win is None:
            continue
        start_t, end_t = win
        revenue_streams.append(
            RevenueStream(
                id=s.id,
                name=s.name,
                start_t=start_t,
                end_t=end_t,
                base_monthly_revenue=s.base_monthly_revenue,
                gross_margin_pct=s.gross_margin_pct,
                collection_days=s.collection_days,
                growth_annual=s.growth_annual,
                ramp=s.ramp,
                seasonality=s.seasonality,
                business_unit_id=s.business_unit_id,
            )
        )

    cost_items: list[CostItem] = []
    for c in effective.cost_items:
        win = _window_t(anchor, c.start_year_month, c.end_year_month, h)
        if win is None:
            continue
        start_t, end_t = win
        cost_items.append(
            CostItem(
                id=c.id,
                name=c.name,
                start_t=start_t,
                end_t=end_t,
                nature=c.nature,
                amount_monthly=c.amount_monthly,
                pct_of_revenue=c.pct_of_revenue,
                payment_days=c.payment_days,
                growth_annual=c.growth_annual,
                seasonality=c.seasonality,
                business_unit_id=c.business_unit_id,
            )
        )

    payroll: list[PayrollLine] = []
    for p in effective.payroll:
        win = _window_t(anchor, p.start_year_month, p.end_year_month, h)
        if win is None:
            continue
        start_t, end_t = win
        payroll.append(
            PayrollLine(
                id=p.id,
                role_name=p.role_name,
                headcount=p.headcount,
                monthly_employer_cost=p.monthly_employer_cost,
                start_t=start_t,
                end_t=end_t,
                payment_days=p.payment_days,
                business_unit_id=p.business_unit_id,
            )
        )

    loans: list[Loan] = []
    for L in effective.loans:
        disbursement_t = months_between(anchor, L.disbursement_year_month)
        # Loan outside horizon: if disbursement >= H and no prior balance, skip
        # MVP: if disbursement_t >= H, exclude; if < 0, treat as already disbursed at t=0
        # with remaining schedule simplification: include from t=0 with outstanding=principal
        # Spec doesn't detail mid-loan run-off; include if any amort months overlap horizon.
        grace = L.grace_months
        # Never send grace_type=none to motor (MODELO §6.5)
        if grace == 0:
            grace_type: str = "capital"  # unused when grace_months=0
            grace_months = 0
        else:
            if L.grace_type not in ("capital", "total"):
                raise SnapshotValidationError(
                    f"loan {L.id}: invalid grace_type for motor"
                )
            grace_type = L.grace_type
            grace_months = grace

        if disbursement_t >= h:
            continue
        skip_drawdown = False
        if disbursement_t < 0:
            # ADR 0001: ya dispuesto → principal vivo sin nueva entrada de caja
            disbursement_t = 0
            skip_drawdown = True

        loans.append(
            Loan(
                id=L.id,
                name=L.name,
                principal=L.principal,
                annual_interest_rate=L.annual_interest_rate,
                term_months=L.term_months,
                amortization_system=L.amortization_system,
                disbursement_t=disbursement_t,
                grace_months=grace_months,
                grace_type=grace_type,  # type: ignore[arg-type]
                origination_fee=L.origination_fee if not skip_drawdown else ZERO,
                rate_type=L.rate_type,
                skip_drawdown=skip_drawdown,
            )
        )

    assets: list[Asset] = []
    for a in effective.assets:
        acq_t = months_between(anchor, a.acquisition_year_month)
        if acq_t >= h:
            continue
        if acq_t < 0:
            # already owned: still depreciate remaining life from anchor
            # months already elapsed = -acq_t; remaining life
            elapsed = -acq_t
            remaining = a.useful_life_months - elapsed
            if remaining <= 0:
                continue
            acq_t = 0
            useful = remaining
            # residual/cost unchanged (MVP simplification)
        else:
            useful = a.useful_life_months

        funding = a.acquisition_funding
        if funding == "loan" and a.funding_loan_id:
            acq_funding = a.funding_loan_id
        elif funding == "mixed" and a.funding_loan_id:
            acq_funding = a.funding_loan_id
        else:
            acq_funding = "cash"

        assets.append(
            Asset(
                id=a.id,
                name=a.name,
                acquisition_cost=a.acquisition_cost,
                acquisition_t=acq_t,
                useful_life_months=useful,
                residual_value=a.residual_value,
                depreciation_method=a.depreciation_method,
                acquisition_funding=acq_funding,
                investment_id=a.investment_id,
            )
        )

    investments: list[Investment] = []
    implicit_one_offs: list[OneOffCashEvent] = []
    for inv in effective.investments:
        capex = []
        for pt in inv.capex_schedule:
            t = months_between(anchor, pt.year_month)
            if 0 <= t < h:
                capex.append(
                    CapexPoint(
                        t=t,
                        amount=pt.amount,
                        includes_vat=pt.includes_vat,
                        label=pt.label,
                    )
                )
        analysis_start_t = months_between(anchor, inv.analysis_start_year_month)
        if analysis_start_t < 0:
            analysis_start_t = 0

        if inv.own_funds_year_month is not None and inv.own_funds_amount is not None:
            ot = months_between(anchor, inv.own_funds_year_month)
            if 0 <= ot < h:
                implicit_one_offs.append(
                    OneOffCashEvent(
                        id=f"own_funds::{inv.id}",
                        t=ot,
                        amount=inv.own_funds_amount,
                        kind="equity_injection",
                    )
                )

        investments.append(
            Investment(
                id=inv.id,
                name=inv.name,
                capex_schedule=tuple(capex),
                analysis_start_t=analysis_start_t,
                analysis_horizon_months=inv.analysis_horizon_months,
                linked_revenue_stream_ids=inv.linked_revenue_stream_ids,
                linked_cost_item_ids=inv.linked_cost_item_ids,
                linked_payroll_ids=inv.linked_payroll_ids,
                linked_loan_ids=inv.linked_loan_ids,
                linked_asset_ids=inv.linked_asset_ids,
                own_funds_t=None,  # expanded as one-off
                own_funds_amount=None,
                discount_rate_annual=inv.discount_rate_annual,
            )
        )

    one_offs: list[OneOffCashEvent] = []
    for o in effective.one_off_cash_events:
        t = months_between(anchor, o.year_month)
        if 0 <= t < h:
            one_offs.append(
                OneOffCashEvent(id=o.id, t=t, amount=o.amount, kind=o.kind)
            )

    # MODELO §6.7.1 / §13.11: no duplicar own_funds + OneOff equity del mismo hecho
    explicit_equity = {
        (o.t, o.amount) for o in one_offs if o.kind == "equity_injection"
    }
    for impl in implicit_one_offs:
        key = (impl.t, impl.amount)
        if key in explicit_equity:
            raise SnapshotValidationError(
                "duplicate own_funds and equity_injection for same month/amount "
                f"(t={impl.t}, amount={impl.amount})"
            )
        one_offs.append(impl)

    calc_input = CalculationInput(
        company=company,
        horizon_months=h,
        discount_rate_annual=scenario.discount_rate_annual,
        auto_finance_deficits=scenario.auto_finance_deficits,
        revenue_streams=tuple(revenue_streams),
        cost_items=tuple(cost_items),
        payroll=tuple(payroll),
        loans=tuple(loans),
        assets=tuple(assets),
        investments=tuple(investments),
        one_off_cash_events=tuple(one_offs),
    )
    inputs_hash = canonical_hash(calc_input)
    return MappedCalculation(
        calculation_input=calc_input,
        inputs_hash=inputs_hash,
        effective_snapshot=effective,
    )
