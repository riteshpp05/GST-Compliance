"""
UC15 GST Compliance Agent — Financial Impact Report Model (Sprint 6)
Comprehensive analytical report aggregating financial exposure, risk linkages, and lineage.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.financial.models.adjustment import FinancialAdjustment
from app.financial.models.aggregate import AggregateFinancialExposure
from app.financial.models.exposure import (
    CounterpartyFinancialExposure,
    PeriodExposureTrend,
    PeriodFinancialExposure,
    RuleFinancialExposure,
)
from app.financial.models.impact import FinancialImpact, ImpactDirection


@dataclass
class FinancialReport:
    """
    Consolidated financial impact report.
    Consumable by UI, downstream AI agents, management reporting, and audit logs.
    """
    report_id: str = field(default_factory=lambda: f"FIN-{uuid.uuid4().hex[:8].upper()}")
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    analysis_period: Optional[str] = None

    # Core Aggregates
    aggregate: AggregateFinancialExposure = field(default_factory=AggregateFinancialExposure)

    # Dimensional Breakdowns
    top_exposures: List[FinancialImpact] = field(default_factory=list)
    counterparty_exposures: List[CounterpartyFinancialExposure] = field(default_factory=list)
    rule_exposures: List[RuleFinancialExposure] = field(default_factory=list)
    period_exposures: List[PeriodFinancialExposure] = field(default_factory=list)
    period_trends: List[PeriodExposureTrend] = field(default_factory=list)
    adjustments: List[FinancialAdjustment] = field(default_factory=list)

    # Executive Summaries & Audit Evidence
    summary: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "analysis_period": self.analysis_period,
            "aggregate": self.aggregate.to_dict(),
            "top_exposures": [i.to_dict() for i in self.top_exposures],
            "counterparty_exposures": [c.to_dict() for c in self.counterparty_exposures],
            "rule_exposures": [r.to_dict() for r in self.rule_exposures],
            "period_exposures": [p.to_dict() for p in self.period_exposures],
            "period_trends": [t.to_dict() for t in self.period_trends],
            "adjustments": [a.to_dict() for a in self.adjustments],
            "summary": self.summary,
            "evidence": self.evidence,
        }

    def to_text_summary(self) -> str:
        """
        Produce a human-readable, executive financial impact summary.
        """
        agg = self.aggregate
        lines = [
            "=" * 65,
            "  UC15 GST Financial Impact & Exposure Intelligence Summary",
            "=" * 65,
            f"Report ID            : {self.report_id}",
            f"Invoices Analyzed    : {agg.total_invoices_analyzed:,}",
            f"Invoices with Impact : {agg.impacted_invoices_count:,}",
            f"Total Quantified Exp : INR {agg.total_potential_exposure:,.2f}",
            f"  - Tax Mismatch Exp : INR {agg.total_tax_difference:,.2f}",
            f"  - Blocked ITC Exp  : INR {agg.total_itc_exposure:,.2f}",
            f"  - Overcharged Tax  : INR {agg.overcharged_tax_total:,.2f}",
            f"  - Undercharged Tax : INR {agg.undercharged_tax_total:,.2f}",
            f"Undetermined Impacts : {agg.undetermined_count} invoice finding(s)",
            "-" * 65,
            "Top Financial Exposures:",
        ]

        if self.top_exposures:
            for idx, imp in enumerate(self.top_exposures[:5], 1):
                exp_str = f"INR {imp.potential_exposure:,.2f}" if imp.potential_exposure is not None else "UNDETERMINED"
                if imp.direction and imp.direction != ImpactDirection.NOT_APPLICABLE:
                    status_info = f"{imp.impact_type.value} | {imp.direction.value} | {imp.calculation_status.value}"
                else:
                    status_info = f"{imp.impact_type.value} | {imp.calculation_status.value}"
                lines.append(
                    f"  {idx}. {imp.invoice_id} ({imp.counterparty_name}) — {exp_str} [{status_info}]"
                )
        else:
            lines.append("  None detected.")

        if self.counterparty_exposures:
            lines.append("-" * 65)
            lines.append("Top Counterparty Exposures:")
            for idx, cp in enumerate(self.counterparty_exposures[:3], 1):
                lines.append(
                    f"  {idx}. {cp.counterparty_name} ({cp.counterparty_id}) — INR {cp.total_potential_exposure:,.2f} ({cp.impacted_invoice_count} invoices)"
                )

        if self.period_trends:
            lines.append("-" * 65)
            lines.append("Period Exposure Trends:")
            for t in self.period_trends[-2:]:
                sign = "+" if (t.absolute_change or Decimal("0.00")) > 0 else ""
                lines.append(
                    f"  - {t.current_period}: INR {t.current_exposure:,.2f} [{t.direction}] ({sign}INR {t.absolute_change or Decimal('0.00'):,.2f})"
                )

        lines.append("=" * 65)
        return "\n".join(lines)
