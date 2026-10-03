"""Finance Twin financial engine — library only, no I/O."""

from financetwin_engine.calc.engine import calculate
from financetwin_engine.calc.loans import LoanSchedule, build_loan_schedule
from financetwin_engine.calc.metrics import InvestmentMetrics, calculate_investment_metrics
from financetwin_engine.mapper import (
    BuildOp,
    CompanyTwinSnapshot,
    ScenarioSpec,
    months_between,
    snapshot_from_dict,
    to_calculation_input,
)
from financetwin_engine.packs import (
    AssetPurchasePack,
    FinancingPack,
    GenericInvestmentPack,
    HiringPack,
    LiquidityPlanPack,
    NewSitePack,
    run_bundle,
    run_variant,
)
from financetwin_engine.model import (
    Asset,
    CapexPoint,
    CostItem,
    Investment,
    Loan,
    OneOffCashEvent,
    PayrollLine,
    RevenueStream,
)
from financetwin_engine.model.calculation import CalculationInput, CalculationResult
from financetwin_engine.model.company import CompanyInput, CompanyPolicy, FiscalConfig
from financetwin_engine.version import ENGINE_VERSION

__version__ = ENGINE_VERSION

__all__ = [
    "__version__",
    "ENGINE_VERSION",
    "calculate",
    "calculate_investment_metrics",
    "build_loan_schedule",
    "InvestmentMetrics",
    "LoanSchedule",
    "CalculationInput",
    "CalculationResult",
    "CompanyInput",
    "CompanyPolicy",
    "FiscalConfig",
    "Asset",
    "CapexPoint",
    "CostItem",
    "Investment",
    "Loan",
    "OneOffCashEvent",
    "PayrollLine",
    "RevenueStream",
    "BuildOp",
    "CompanyTwinSnapshot",
    "ScenarioSpec",
    "months_between",
    "snapshot_from_dict",
    "to_calculation_input",
    "NewSitePack",
    "FinancingPack",
    "AssetPurchasePack",
    "HiringPack",
    "GenericInvestmentPack",
    "LiquidityPlanPack",
    "run_bundle",
    "run_variant",
]
