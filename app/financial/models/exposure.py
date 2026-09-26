"""
UC15 GST Compliance Agent — Financial Exposure Summary Models (Sprint 6)
Provides multi-dimensional exposure aggregation across counterparties, rules, and time periods.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CounterpartyFinancialExposure:
    """
    Longitudinal financial exposure profile for a vendor (AP) or customer (AR).
    """
    counterparty_id: str
    counterparty_name: str
    direction: str = "AR"

    # Invoicing and Exposure Aggregates
    invoice_count: int = 0
    impacted_invoice_count: int = 0
    total_potential_exposure: Decimal = Decimal("0.00")
    tax_difference_exposure: Decimal = Decimal("0.00")
    itc_exposure: Decimal = Decimal("0.00")
    overcharged_tax_total: Decimal = Decimal("0.00")
    undercharged_tax_total: Decimal = Decimal("0.00")
    undetermined_count: int = 0

    # Rule and Transaction Breakdowns
    top_exposure_rules: List[Tuple[str, Decimal]] = field(default_factory=list)
    affected_invoices: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counterparty_id": self.counterparty_id,
            "counterparty_name": self.counterparty_name,
            "direction": self.direction,
            "invoice_count": self.invoice_count,
            "impacted_invoice_count": self.impacted_invoice_count,
            "total_potential_exposure": float(self.total_potential_exposure),
            "tax_difference_exposure": float(self.tax_difference_exposure),
            "itc_exposure": float(self.itc_exposure),
            "overcharged_tax_total": float(self.overcharged_tax_total),
            "undercharged_tax_total": float(self.undercharged_tax_total),
            "undetermined_count": self.undetermined_count,
            "top_exposure_rules": [{"rule_id": r, "exposure": float(e)} for r, e in self.top_exposure_rules],
            "affected_invoices": self.affected_invoices,
        }


@dataclass
class RuleFinancialExposure:
    """
    Financial exposure aggregate associated with a specific statutory rule.
    """
    rule_id: str
    rule_category: str
    affected_invoice_count: int = 0
    total_potential_exposure: Decimal = Decimal("0.00")
    calculation_status_counts: Dict[str, int] = field(default_factory=dict)
    affected_invoices: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_category": self.rule_category,
            "affected_invoice_count": self.affected_invoice_count,
            "total_potential_exposure": float(self.total_potential_exposure),
            "calculation_status_counts": self.calculation_status_counts,
            "affected_invoices": self.affected_invoices,
        }


@dataclass
class PeriodFinancialExposure:
    """
    Financial exposure aggregated over a discrete time period (Monthly, Quarterly, etc.).
    """
    period_key: str
    period_type: str = "MONTHLY"
    invoice_count: int = 0
    impacted_invoice_count: int = 0
    total_potential_exposure: Decimal = Decimal("0.00")
    tax_difference_exposure: Decimal = Decimal("0.00")
    itc_exposure: Decimal = Decimal("0.00")
    overcharged_tax_total: Decimal = Decimal("0.00")
    undercharged_tax_total: Decimal = Decimal("0.00")
    undetermined_count: int = 0
    affected_invoices: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_key": self.period_key,
            "period_type": self.period_type,
            "invoice_count": self.invoice_count,
            "impacted_invoice_count": self.impacted_invoice_count,
            "total_potential_exposure": float(self.total_potential_exposure),
            "tax_difference_exposure": float(self.tax_difference_exposure),
            "itc_exposure": float(self.itc_exposure),
            "overcharged_tax_total": float(self.overcharged_tax_total),
            "undercharged_tax_total": float(self.undercharged_tax_total),
            "undetermined_count": self.undetermined_count,
            "affected_invoices": self.affected_invoices,
        }


@dataclass
class PeriodExposureTrend:
    """
    Period-over-period trajectory of quantified potential financial exposure.
    """
    current_period: str
    previous_period: Optional[str] = None
    current_exposure: Decimal = Decimal("0.00")
    previous_exposure: Optional[Decimal] = None
    absolute_change: Optional[Decimal] = None
    percentage_change: Optional[float] = None
    direction: str = "INSUFFICIENT_DATA"  # INCREASING | DECREASING | STABLE | INSUFFICIENT_DATA
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_period": self.current_period,
            "previous_period": self.previous_period,
            "current_exposure": float(self.current_exposure),
            "previous_exposure": float(self.previous_exposure) if self.previous_exposure is not None else None,
            "absolute_change": float(self.absolute_change) if self.absolute_change is not None else None,
            "percentage_change": self.percentage_change,
            "direction": self.direction,
            "description": self.description,
        }
