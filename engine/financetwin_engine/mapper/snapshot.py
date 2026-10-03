"""CompanyTwinSnapshot schemas — MODELO §5.2–§6 (dataclasses = equivalente Pydantic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Sequence

from financetwin_engine.calc.decimal_money import D

SCHEMA_VERSION = "1.0"

RevenueType = Literal["recurring", "transactional", "project"]
CostNature = Literal["fixed", "variable_pct_revenue"]
GraceTypeSnap = Literal["capital", "total", "none"]
AmortizationSystem = Literal["french", "linear", "bullet"]
DepreciationMethod = Literal["straight_line", "declining_simple"]
AcquisitionFunding = Literal["cash", "loan", "mixed"]
DataOrigin = Literal["historical", "user", "sector", "calibrated", "imported", "calculated"]
Confidence = Literal["high", "medium", "low"]
OneOffKind = Literal["equity_injection", "dividend", "other_in", "other_out", "capex"]
VatSettlement = Literal["monthly", "quarterly"]
CorpTaxPaymentMode = Literal["none", "annual_end", "quarterly_approx"]


def _dec(value: Any, default: Decimal | None = None) -> Decimal:
    if value is None:
        if default is not None:
            return default
        raise ValueError("missing Decimal value")
    if isinstance(value, float):
        raise TypeError("float not allowed; use string/Decimal")
    return D(value)


@dataclass(frozen=True)
class SnapshotCompany:
    currency: str = "EUR"
    opening_cash: Decimal = Decimal("0")
    default_purchase_payment_days: int = 30


@dataclass(frozen=True)
class SnapshotFiscal:
    vat_rate: Decimal = Decimal("0.21")
    vat_settlement: VatSettlement = "quarterly"
    vat_payment_lag_months: int = 1
    corp_tax_rate: Decimal = Decimal("0.25")
    corp_tax_payment_mode: CorpTaxPaymentMode = "quarterly_approx"


@dataclass(frozen=True)
class SnapshotPolicies:
    min_cash: Decimal = Decimal("0")
    max_debt_ebitda: Decimal | None = None
    min_dscr: Decimal | None = None
    max_payback_months: int | None = None
    min_irr: Decimal | None = None
    max_capex_pct_cash: Decimal | None = None


@dataclass(frozen=True)
class BusinessUnitSnap:
    id: str
    name: str
    is_active: bool = True
    unit_type: str | None = None
    start_year_month: str | None = None


@dataclass(frozen=True)
class RevenueStreamSnap:
    id: str
    name: str
    revenue_type: RevenueType
    start_year_month: str
    base_monthly_revenue: Decimal
    gross_margin_pct: Decimal
    collection_days: int
    origin: DataOrigin = "user"
    confidence: Confidence = "medium"
    end_year_month: str | None = None
    business_unit_id: str | None = None
    ramp: tuple[Decimal, ...] | None = None
    seasonality: tuple[Decimal, ...] | None = None
    growth_annual: Decimal = Decimal("0")
    notes: str | None = None


@dataclass(frozen=True)
class CostItemSnap:
    id: str
    name: str
    nature: CostNature
    start_year_month: str
    payment_days: int
    origin: DataOrigin = "user"
    confidence: Confidence = "medium"
    end_year_month: str | None = None
    business_unit_id: str | None = None
    amount_monthly: Decimal | None = None
    pct_of_revenue: Decimal | None = None
    growth_annual: Decimal = Decimal("0")
    seasonality: tuple[Decimal, ...] | None = None
    is_vatable: bool = True
    notes: str | None = None


@dataclass(frozen=True)
class PayrollLineSnap:
    id: str
    role_name: str
    headcount: int
    monthly_employer_cost: Decimal
    start_year_month: str
    payment_days: int = 0
    origin: DataOrigin = "user"
    confidence: Confidence = "medium"
    end_year_month: str | None = None
    business_unit_id: str | None = None


@dataclass(frozen=True)
class LoanSnap:
    id: str
    name: str
    principal: Decimal
    annual_interest_rate: Decimal
    term_months: int
    amortization_system: AmortizationSystem
    disbursement_year_month: str
    rate_type: Literal["fixed"] = "fixed"
    grace_months: int = 0
    grace_type: GraceTypeSnap = "none"
    origination_fee: Decimal = Decimal("0")
    origin: DataOrigin = "user"
    confidence: Confidence = "medium"
    lender: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class AssetSnap:
    id: str
    name: str
    acquisition_cost: Decimal
    acquisition_year_month: str
    useful_life_months: int
    depreciation_method: DepreciationMethod
    acquisition_funding: AcquisitionFunding
    residual_value: Decimal = Decimal("0")
    funding_loan_id: str | None = None
    investment_id: str | None = None
    origin: DataOrigin = "user"
    confidence: Confidence = "medium"
    asset_type: str | None = None


@dataclass(frozen=True)
class CapexPointSnap:
    year_month: str
    amount: Decimal
    includes_vat: bool = False
    label: str | None = None


@dataclass(frozen=True)
class InvestmentSnap:
    id: str
    name: str
    capex_schedule: tuple[CapexPointSnap, ...]
    analysis_start_year_month: str
    analysis_horizon_months: int
    linked_revenue_stream_ids: tuple[str, ...] = ()
    linked_cost_item_ids: tuple[str, ...] = ()
    linked_payroll_ids: tuple[str, ...] = ()
    linked_loan_ids: tuple[str, ...] = ()
    linked_asset_ids: tuple[str, ...] = ()
    own_funds_year_month: str | None = None
    own_funds_amount: Decimal | None = None
    discount_rate_annual: Decimal | None = None
    decision_pack_id: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class OneOffCashEventSnap:
    id: str
    year_month: str
    amount: Decimal
    kind: OneOffKind


@dataclass(frozen=True)
class AssumptionSnap:
    id: str
    key: str
    value: str
    value_type: Literal["money", "rate", "count", "text", "bool"] = "text"


@dataclass(frozen=True)
class CompanyTwinSnapshot:
    schema_version: str
    company: SnapshotCompany
    fiscal: SnapshotFiscal = field(default_factory=SnapshotFiscal)
    policies: SnapshotPolicies = field(default_factory=SnapshotPolicies)
    business_units: tuple[BusinessUnitSnap, ...] = ()
    revenue_streams: tuple[RevenueStreamSnap, ...] = ()
    cost_items: tuple[CostItemSnap, ...] = ()
    payroll: tuple[PayrollLineSnap, ...] = ()
    loans: tuple[LoanSnap, ...] = ()
    assets: tuple[AssetSnap, ...] = ()
    investments: tuple[InvestmentSnap, ...] = ()
    one_off_cash_events: tuple[OneOffCashEventSnap, ...] = ()
    assumptions: tuple[AssumptionSnap, ...] = ()


class SnapshotValidationError(ValueError):
    pass


def validate_snapshot(snapshot: CompanyTwinSnapshot) -> None:
    if snapshot.schema_version != SCHEMA_VERSION:
        raise SnapshotValidationError(
            f"schema_version must be {SCHEMA_VERSION!r}, got {snapshot.schema_version!r}"
        )
    if snapshot.company.currency != "EUR":
        raise SnapshotValidationError("MVP currency must be EUR")

    # Loan grace invariants
    for loan in snapshot.loans:
        if loan.grace_months == 0 and loan.grace_type != "none":
            raise SnapshotValidationError(
                f"loan {loan.id}: grace_months=0 requires grace_type=none"
            )
        if loan.grace_months > 0 and loan.grace_type not in ("capital", "total"):
            raise SnapshotValidationError(
                f"loan {loan.id}: grace_months>0 requires grace_type capital|total"
            )

    # Asset ↔ Investment bidirectionality
    inv_by_id = {i.id: i for i in snapshot.investments}
    for asset in snapshot.assets:
        if asset.investment_id is None:
            continue
        inv = inv_by_id.get(asset.investment_id)
        if inv is None:
            raise SnapshotValidationError(
                f"asset {asset.id}: investment_id {asset.investment_id} not found"
            )
        if asset.id not in inv.linked_asset_ids:
            raise SnapshotValidationError(
                f"asset {asset.id} ↔ investment {inv.id}: missing from linked_asset_ids"
            )
    for inv in snapshot.investments:
        for aid in inv.linked_asset_ids:
            asset = next((a for a in snapshot.assets if a.id == aid), None)
            if asset is None:
                raise SnapshotValidationError(
                    f"investment {inv.id}: linked asset {aid} not found"
                )
            if asset.investment_id != inv.id:
                raise SnapshotValidationError(
                    f"investment {inv.id} ↔ asset {aid}: investment_id mismatch"
                )


def snapshot_from_dict(
    data: dict[str, Any],
    *,
    validate: bool = True,
) -> CompanyTwinSnapshot:
    """Parse + optionally validate a snapshot dict (JSON-like)."""
    if not isinstance(data, dict):
        raise SnapshotValidationError("snapshot must be an object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SnapshotValidationError(
            f"schema_version must be {SCHEMA_VERSION!r}"
        )

    company_raw = data.get("company") or {}
    company = SnapshotCompany(
        currency=company_raw.get("currency", "EUR"),
        opening_cash=_dec(company_raw.get("opening_cash", "0")),
        default_purchase_payment_days=int(
            company_raw.get("default_purchase_payment_days", 30)
        ),
    )
    fiscal_raw = data.get("fiscal") or {}
    fiscal = SnapshotFiscal(
        vat_rate=_dec(fiscal_raw.get("vat_rate", "0.21")),
        vat_settlement=fiscal_raw.get("vat_settlement", "quarterly"),
        vat_payment_lag_months=int(fiscal_raw.get("vat_payment_lag_months", 1)),
        corp_tax_rate=_dec(fiscal_raw.get("corp_tax_rate", "0.25")),
        corp_tax_payment_mode=fiscal_raw.get("corp_tax_payment_mode", "quarterly_approx"),
    )
    pol_raw = data.get("policies") or {}
    policies = SnapshotPolicies(
        min_cash=_dec(pol_raw.get("min_cash", "0")),
        max_debt_ebitda=_dec(pol_raw["max_debt_ebitda"]) if pol_raw.get("max_debt_ebitda") is not None else None,
        min_dscr=_dec(pol_raw["min_dscr"]) if pol_raw.get("min_dscr") is not None else None,
        max_payback_months=pol_raw.get("max_payback_months"),
        min_irr=_dec(pol_raw["min_irr"]) if pol_raw.get("min_irr") is not None else None,
        max_capex_pct_cash=_dec(pol_raw["max_capex_pct_cash"]) if pol_raw.get("max_capex_pct_cash") is not None else None,
    )

    def _ramp(v: Any) -> tuple[Decimal, ...] | None:
        if v is None:
            return None
        return tuple(_dec(x) for x in v)

    revenue_streams = tuple(
        RevenueStreamSnap(
            id=r["id"],
            name=r["name"],
            revenue_type=r["revenue_type"],
            start_year_month=r["start_year_month"],
            end_year_month=r.get("end_year_month"),
            base_monthly_revenue=_dec(r["base_monthly_revenue"]),
            gross_margin_pct=_dec(r["gross_margin_pct"]),
            collection_days=int(r["collection_days"]),
            growth_annual=_dec(r.get("growth_annual", "0")),
            ramp=_ramp(r.get("ramp")),
            seasonality=_ramp(r.get("seasonality")),
            business_unit_id=r.get("business_unit_id"),
            origin=r.get("origin", "user"),
            confidence=r.get("confidence", "medium"),
            notes=r.get("notes"),
        )
        for r in data.get("revenue_streams") or []
    )
    cost_items = tuple(
        CostItemSnap(
            id=c["id"],
            name=c["name"],
            nature=c["nature"],
            start_year_month=c["start_year_month"],
            end_year_month=c.get("end_year_month"),
            payment_days=int(c["payment_days"]),
            amount_monthly=_dec(c["amount_monthly"]) if c.get("amount_monthly") is not None else None,
            pct_of_revenue=_dec(c["pct_of_revenue"]) if c.get("pct_of_revenue") is not None else None,
            growth_annual=_dec(c.get("growth_annual", "0")),
            seasonality=_ramp(c.get("seasonality")),
            business_unit_id=c.get("business_unit_id"),
            is_vatable=bool(c.get("is_vatable", True)),
            origin=c.get("origin", "user"),
            confidence=c.get("confidence", "medium"),
            notes=c.get("notes"),
        )
        for c in data.get("cost_items") or []
    )
    payroll = tuple(
        PayrollLineSnap(
            id=p["id"],
            role_name=p["role_name"],
            headcount=int(p["headcount"]),
            monthly_employer_cost=_dec(p["monthly_employer_cost"]),
            start_year_month=p["start_year_month"],
            end_year_month=p.get("end_year_month"),
            payment_days=int(p.get("payment_days", 0)),
            business_unit_id=p.get("business_unit_id"),
            origin=p.get("origin", "user"),
            confidence=p.get("confidence", "medium"),
        )
        for p in data.get("payroll") or []
    )
    loans = tuple(
        LoanSnap(
            id=L["id"],
            name=L["name"],
            principal=_dec(L["principal"]),
            annual_interest_rate=_dec(L["annual_interest_rate"]),
            term_months=int(L["term_months"]),
            amortization_system=L["amortization_system"],
            disbursement_year_month=L["disbursement_year_month"],
            rate_type=L.get("rate_type", "fixed"),
            grace_months=int(L.get("grace_months", 0)),
            grace_type=L.get("grace_type", "none"),
            origination_fee=_dec(L.get("origination_fee", "0")),
            origin=L.get("origin", "user"),
            confidence=L.get("confidence", "medium"),
            lender=L.get("lender"),
            notes=L.get("notes"),
        )
        for L in data.get("loans") or []
    )
    assets = tuple(
        AssetSnap(
            id=a["id"],
            name=a["name"],
            acquisition_cost=_dec(a["acquisition_cost"]),
            acquisition_year_month=a["acquisition_year_month"],
            useful_life_months=int(a["useful_life_months"]),
            residual_value=_dec(a.get("residual_value", "0")),
            depreciation_method=a["depreciation_method"],
            acquisition_funding=a["acquisition_funding"],
            funding_loan_id=a.get("funding_loan_id"),
            investment_id=a.get("investment_id"),
            origin=a.get("origin", "user"),
            confidence=a.get("confidence", "medium"),
            asset_type=a.get("asset_type"),
        )
        for a in data.get("assets") or []
    )
    investments = tuple(
        InvestmentSnap(
            id=i["id"],
            name=i["name"],
            capex_schedule=tuple(
                CapexPointSnap(
                    year_month=pt["year_month"],
                    amount=_dec(pt["amount"]),
                    includes_vat=bool(pt.get("includes_vat", False)),
                    label=pt.get("label"),
                )
                for pt in i.get("capex_schedule") or []
            ),
            analysis_start_year_month=i["analysis_start_year_month"],
            analysis_horizon_months=int(i["analysis_horizon_months"]),
            linked_revenue_stream_ids=tuple(i.get("linked_revenue_stream_ids") or ()),
            linked_cost_item_ids=tuple(i.get("linked_cost_item_ids") or ()),
            linked_payroll_ids=tuple(i.get("linked_payroll_ids") or ()),
            linked_loan_ids=tuple(i.get("linked_loan_ids") or ()),
            linked_asset_ids=tuple(i.get("linked_asset_ids") or ()),
            own_funds_year_month=i.get("own_funds_year_month"),
            own_funds_amount=_dec(i["own_funds_amount"]) if i.get("own_funds_amount") is not None else None,
            discount_rate_annual=_dec(i["discount_rate_annual"]) if i.get("discount_rate_annual") is not None else None,
            decision_pack_id=i.get("decision_pack_id"),
            notes=i.get("notes"),
        )
        for i in data.get("investments") or []
    )
    one_offs = tuple(
        OneOffCashEventSnap(
            id=o["id"],
            year_month=o["year_month"],
            amount=_dec(o["amount"]),
            kind=o["kind"],
        )
        for o in data.get("one_off_cash_events") or []
    )
    assumptions = tuple(
        AssumptionSnap(
            id=a["id"],
            key=a["key"],
            value=str(a["value"]),
            value_type=a.get("value_type", "text"),
        )
        for a in data.get("assumptions") or []
    )
    business_units = tuple(
        BusinessUnitSnap(
            id=b["id"],
            name=b["name"],
            is_active=bool(b.get("is_active", True)),
            unit_type=b.get("unit_type"),
            start_year_month=b.get("start_year_month"),
        )
        for b in data.get("business_units") or []
    )

    snap = CompanyTwinSnapshot(
        schema_version=SCHEMA_VERSION,
        company=company,
        fiscal=fiscal,
        policies=policies,
        business_units=business_units,
        revenue_streams=revenue_streams,
        cost_items=cost_items,
        payroll=payroll,
        loans=loans,
        assets=assets,
        investments=investments,
        one_off_cash_events=one_offs,
        assumptions=assumptions,
    )
    if validate:
        validate_snapshot(snap)
    return snap
