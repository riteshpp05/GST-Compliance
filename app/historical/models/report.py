"""
UC15 GST Compliance Agent — Historical Intelligence Report Model (Sprint 5)
Comprehensive analytical report aggregating time-series metrics, trends, rule recurrence,
counterparty profiles, data quality findings, and retroactive audit insights.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.historical.models.audit import HistoricalAuditComparison
from app.historical.models.counterparty import CounterpartyProfile, RecurringCounterpartyPattern
from app.historical.models.data_quality import DataQualityPattern
from app.historical.models.pattern import RuleFailurePattern
from app.historical.models.period import PeriodMetrics, PeriodType
from app.historical.models.trend import PeriodTrend


@dataclass
class HistoricalReport:
    """
    Complete consolidated historical intelligence report produced by HistoricalService.
    Consumable by UI, downstream AI agent, executive reporting, and audit logs.
    """
    report_id: str
    period_type: PeriodType = PeriodType.MONTHLY
    analysis_period: Optional[str] = None
    previous_period: Optional[str] = None

    # Global Summaries
    total_invoices_analyzed: int = 0
    total_periods_covered: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Analytical Components
    periods: List[PeriodMetrics] = field(default_factory=list)
    trends: List[PeriodTrend] = field(default_factory=list)
    rule_patterns: List[RuleFailurePattern] = field(default_factory=list)
    counterparty_profiles: List[CounterpartyProfile] = field(default_factory=list)
    counterparty_patterns: List[RecurringCounterpartyPattern] = field(default_factory=list)
    data_quality_patterns: List[DataQualityPattern] = field(default_factory=list)
    audit_results: List[HistoricalAuditComparison] = field(default_factory=list)

    # Executive Summary & Traceable Evidence
    summary: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)

    # Aliases for Section 17 compatibility
    @property
    def period_metrics(self) -> List[PeriodMetrics]:
        return self.periods

    @property
    def recurring_rule_patterns(self) -> List[RuleFailurePattern]:
        return self.rule_patterns

    @property
    def historical_audit_results(self) -> List[HistoricalAuditComparison]:
        return self.audit_results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "period_type": self.period_type.value,
            "analysis_period": self.analysis_period,
            "previous_period": self.previous_period,
            "total_invoices_analyzed": self.total_invoices_analyzed,
            "total_periods_covered": self.total_periods_covered,
            "generated_at": self.generated_at,
            "periods": [p.to_dict() for p in self.periods],
            "trends": [t.to_dict() for t in self.trends],
            "rule_patterns": [r.to_dict() for r in self.rule_patterns],
            "counterparty_profiles": [c.to_dict() for c in self.counterparty_profiles],
            "counterparty_patterns": [cp.to_dict() for cp in self.counterparty_patterns],
            "data_quality_patterns": [dq.to_dict() for dq in self.data_quality_patterns],
            "audit_results": [a.to_dict() for a in self.audit_results],
            "summary": self.summary,
            "evidence": self.evidence,
        }

    def to_text_summary(self) -> str:
        """
        Produce a human-readable and executive summary conforming to Sprint 5 specification.
        """
        lines = [
            "=" * 60,
            "  UC15 GST Historical Intelligence & Time-Series Audit",
            "=" * 60,
            f"Report ID : {self.report_id}",
            f"Period    : {self.analysis_period or 'Full Historical Range'}",
            f"Invoices  : {self.total_invoices_analyzed:,}",
        ]

        # Latest period overview if available
        if self.periods:
            latest = self.periods[-1]
            lines.extend([
                f"Compliant       : {latest.compliant_count} ({latest.compliance_rate}%)",
                f"Needs Review    : {latest.needs_review_count} ({latest.needs_review_rate}%)",
                f"Non-Compliant   : {latest.non_compliant_count} ({latest.non_compliance_rate}%)",
            ])

        # Trend overview
        if self.trends:
            latest_trend = self.trends[-1]
            sign = "+" if (latest_trend.absolute_change_pp or 0) > 0 else ""
            lines.append(f"Trend           : {latest_trend.direction.value} ({sign}{latest_trend.absolute_change_pp or 0.0} pp)")

        # Recurring rules
        lines.append("-" * 60)
        lines.append("Top Recurring Rule Patterns:")
        if self.rule_patterns:
            for i, p in enumerate(self.rule_patterns[:5], 1):
                lines.append(f"  {i}. Rule {p.rule_id} [{p.classification.value}] — {p.total_failures} failures across {len(p.periods_observed)} periods")
        else:
            lines.append("  None detected.")

        # Counterparty patterns
        lines.append("-" * 60)
        lines.append("Counterparty Recurring Patterns:")
        if self.counterparty_patterns:
            for i, cp in enumerate(self.counterparty_patterns[:3], 1):
                lines.append(f"  {i}. {cp.counterparty_name} ({cp.counterparty_id}) — {cp.occurrences} repeated {cp.issue_type}")
        else:
            lines.append("  None detected.")

        # Data quality patterns
        lines.append("-" * 60)
        lines.append("Data Quality Defect Patterns:")
        if self.data_quality_patterns:
            for i, dq in enumerate(self.data_quality_patterns[:3], 1):
                lines.append(f"  {i}. {dq.issue_type} — {dq.occurrence_count} invoices ({dq.occurrence_rate}%)")
        else:
            lines.append("  None detected.")

        lines.append("=" * 60)
        return "\n".join(lines)
