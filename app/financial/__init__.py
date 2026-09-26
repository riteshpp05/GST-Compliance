"""
app.financial
=============
Sprint 6 — Financial Impact & Exposure Intelligence.

Provides deterministic monetary calculation of GST compliance issues,
portfolio-level exposure aggregation, counterparty/rule/period analytics,
top exposure ranking, and audit-ready financial reporting.
"""

from app.financial.models import (
    FinancialImpact,
    FinancialImpactType,
    ImpactDirection,
    CalculationStatus,
    round_monetary,
    CounterpartyFinancialExposure,
    RuleFinancialExposure,
    PeriodFinancialExposure,
    PeriodExposureTrend,
    FinancialAdjustment,
    AggregateFinancialExposure,
    FinancialReport,
)
from app.financial.calculators import (
    TaxDifferenceCalculator,
    parse_tax_rate,
    InvoiceExposureCalculator,
    AggregateCalculator,
)
from app.financial.repositories import (
    BaseFinancialRepository,
    InMemoryFinancialRepository,
)
from app.financial.services import FinancialService

__all__ = [
    # Models
    "FinancialImpact",
    "FinancialImpactType",
    "ImpactDirection",
    "CalculationStatus",
    "round_monetary",
    "CounterpartyFinancialExposure",
    "RuleFinancialExposure",
    "PeriodFinancialExposure",
    "PeriodExposureTrend",
    "FinancialAdjustment",
    "AggregateFinancialExposure",
    "FinancialReport",
    # Calculators
    "TaxDifferenceCalculator",
    "parse_tax_rate",
    "InvoiceExposureCalculator",
    "AggregateCalculator",
    # Repositories
    "BaseFinancialRepository",
    "InMemoryFinancialRepository",
    # Services
    "FinancialService",
]
