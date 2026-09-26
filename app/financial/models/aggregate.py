"""
UC15 GST Compliance Agent — Aggregate Financial Exposure Model (Sprint 6)
Consolidates invoice-level financial impacts into a unified, traceable portfolio exposure summary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List


@dataclass
class AggregateFinancialExposure:
    """
    Portfolio-wide aggregated financial exposure.
    Strictly excludes UNDETERMINED impacts from monetary totals while tracking their occurrence.
    """
    total_invoices_analyzed: int = 0
    impacted_invoices_count: int = 0
    clean_invoices_count: int = 0

    # Monetary Quantified Totals (Decimal precision)
    total_potential_exposure: Decimal = Decimal("0.00")
    total_tax_difference: Decimal = Decimal("0.00")
    total_itc_exposure: Decimal = Decimal("0.00")
    overcharged_tax_total: Decimal = Decimal("0.00")
    undercharged_tax_total: Decimal = Decimal("0.00")

    # Calculation Status Distribution Counts
    calculated_count: int = 0
    partially_calculated_count: int = 0
    undetermined_count: int = 0
    not_applicable_count: int = 0

    # Dimension Breakdowns
    by_rule: Dict[str, Decimal] = field(default_factory=dict)
    by_counterparty: Dict[str, Decimal] = field(default_factory=dict)
    by_period: Dict[str, Decimal] = field(default_factory=dict)

    # Lineage and Blast-Radius Traceability
    affected_invoices: List[str] = field(default_factory=list)
    affected_counterparties: List[str] = field(default_factory=list)
    rule_ids: List[str] = field(default_factory=list)
    periods: List[str] = field(default_factory=list)
    currency: str = "INR"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_invoices_analyzed": self.total_invoices_analyzed,
            "impacted_invoices_count": self.impacted_invoice_count if hasattr(self, 'impacted_invoice_count') else self.impacted_invoices_count,
            "clean_invoices_count": self.clean_invoices_count,
            "total_potential_exposure": float(self.total_potential_exposure),
            "total_tax_difference": float(self.total_tax_difference),
            "total_itc_exposure": float(self.total_itc_exposure),
            "overcharged_tax_total": float(self.overcharged_tax_total),
            "undercharged_tax_total": float(self.undercharged_tax_total),
            "calculated_count": self.calculated_count,
            "partially_calculated_count": self.partially_calculated_count,
            "undetermined_count": self.undetermined_count,
            "not_applicable_count": self.not_applicable_count,
            "by_rule": {k: float(v) for k, v in self.by_rule.items()},
            "by_counterparty": {k: float(v) for k, v in self.by_counterparty.items()},
            "by_period": {k: float(v) for k, v in self.by_period.items()},
            "affected_invoices": self.affected_invoices,
            "affected_counterparties": self.affected_counterparties,
            "rule_ids": self.rule_ids,
            "periods": self.periods,
            "currency": self.currency,
        }
