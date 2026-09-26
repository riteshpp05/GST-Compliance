"""
UC15 GST Compliance Agent — Historical Intelligence Service (Sprint 5)
Unified facade service orchestrating time-series aggregation, trend analysis,
rule failure pattern classification, counterparty profiling, and retroactive audit.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.historical.analyzers.audit_analyzer import HistoricalAuditAnalyzer
from app.historical.analyzers.counterparty_analyzer import CounterpartyAnalyzer
from app.historical.analyzers.dq_analyzer import DataQualityAnalyzer
from app.historical.analyzers.period_analyzer import PeriodAnalyzer
from app.historical.analyzers.rule_pattern_analyzer import RulePatternAnalyzer
from app.historical.analyzers.trend_analyzer import TrendAnalyzer
from app.historical.config.historical_config import HistoricalConfig, default_historical_config
from app.historical.models.audit import HistoricalAuditComparison
from app.historical.models.counterparty import CounterpartyProfile, RecurringCounterpartyPattern
from app.historical.models.data_quality import DataQualityPattern
from app.historical.models.pattern import RuleFailurePattern
from app.historical.models.period import PeriodMetrics, PeriodType
from app.historical.models.record import HistoricalRecord
from app.historical.models.report import HistoricalReport
from app.historical.models.trend import PeriodTrend
from app.historical.repositories.base import BaseHistoricalRepository
from app.historical.repositories.in_memory import InMemoryHistoricalRepository
from app.reference.services.reference_service import ReferenceService


class HistoricalService:
    """
    Primary interface for Historical Intelligence (Sprint 5).
    Consumes compliance decisions, stores historical records, and provides multi-dimensional time-series audit.
    """

    def __init__(
        self,
        repository: Optional[BaseHistoricalRepository] = None,
        config: Optional[HistoricalConfig] = None,
        reference_service: Optional[ReferenceService] = None,
    ) -> None:
        self.repository = repository or InMemoryHistoricalRepository()
        self.config = config or default_historical_config
        self.reference_service = reference_service

        # Initialize analyzers
        self.period_analyzer = PeriodAnalyzer()
        self.trend_analyzer = TrendAnalyzer(config=self.config)
        self.rule_pattern_analyzer = RulePatternAnalyzer(config=self.config)
        self.counterparty_analyzer = CounterpartyAnalyzer(config=self.config)
        self.dq_analyzer = DataQualityAnalyzer(config=self.config)
        self.audit_analyzer = HistoricalAuditAnalyzer(reference_service=self.reference_service)

    def record_decision(
        self,
        decision: ComplianceDecision,
        invoice: Optional[Invoice] = None,
    ) -> HistoricalRecord:
        """
        Convert a ComplianceDecision into a HistoricalRecord and save it to the repository.
        """
        record = HistoricalRecord.from_compliance_decision(decision, invoice=invoice)
        self.repository.add(record)
        return record

    def record_batch(
        self,
        decisions: List[ComplianceDecision],
        invoices: Optional[List[Invoice]] = None,
    ) -> List[HistoricalRecord]:
        """
        Ingest a batch of ComplianceDecisions into the historical intelligence layer.
        """
        inv_map = {inv.invoice_number: inv for inv in (invoices or [])}
        records: List[HistoricalRecord] = []
        for d in decisions:
            inv = inv_map.get(d.invoice_no)
            rec = HistoricalRecord.from_compliance_decision(d, invoice=inv)
            records.append(rec)
        self.repository.add_batch(records)
        return records

    def get_period_metrics(self, period_type: PeriodType = PeriodType.MONTHLY) -> List[PeriodMetrics]:
        """Aggregate stored records into chronological period metrics."""
        records = self.repository.list_all()
        return self.period_analyzer.aggregate(records, period_type=period_type)

    def get_trends(self, period_type: PeriodType = PeriodType.MONTHLY) -> List[PeriodTrend]:
        """Calculate period-over-period compliance rate trends."""
        periods = self.get_period_metrics(period_type=period_type)
        return self.trend_analyzer.analyze_trends(periods)

    def get_rule_patterns(self, period_type: PeriodType = PeriodType.MONTHLY) -> List[RuleFailurePattern]:
        """Identify and classify recurring rule failure patterns."""
        records = self.repository.list_all()
        periods = self.period_analyzer.aggregate(records, period_type=period_type)
        return self.rule_pattern_analyzer.analyze(records, periods)

    def get_counterparty_profiles(self, period_type: PeriodType = PeriodType.MONTHLY) -> List[CounterpartyProfile]:
        """Build historical compliance profiles for all vendors/customers."""
        records = self.repository.list_all()
        periods = self.period_analyzer.aggregate(records, period_type=period_type)
        return self.counterparty_analyzer.build_profiles(records, periods)

    def get_recurring_counterparty_patterns(self, period_type: PeriodType = PeriodType.MONTHLY) -> List[RecurringCounterpartyPattern]:
        """Detect systemic recurring anomalies from specific counterparties."""
        records = self.repository.list_all()
        periods = self.period_analyzer.aggregate(records, period_type=period_type)
        return self.counterparty_analyzer.detect_recurring_patterns(records, periods)

    def get_data_quality_patterns(self, period_type: PeriodType = PeriodType.MONTHLY) -> List[DataQualityPattern]:
        """Analyze recurring data defects and field omission patterns."""
        records = self.repository.list_all()
        periods = self.period_analyzer.aggregate(records, period_type=period_type)
        return self.dq_analyzer.analyze(records, periods)

    def perform_historical_audit(
        self,
        invoices: Optional[Dict[str, Invoice]] = None,
    ) -> List[HistoricalAuditComparison]:
        """
        Audit all historical records using transaction-date effective reference intelligence.
        """
        records = self.repository.list_all()
        return self.audit_analyzer.audit_batch(records, invoices=invoices)

    def generate_report(
        self,
        period_type: PeriodType = PeriodType.MONTHLY,
        target_period: Optional[str] = None,
    ) -> HistoricalReport:
        """
        Generate a complete, explainable Historical Intelligence Report across all analytical dimensions.
        """
        records = self.repository.list_all()
        periods = self.period_analyzer.aggregate(records, period_type=period_type)
        trends = self.trend_analyzer.analyze_trends(periods)
        rule_patterns = self.rule_pattern_analyzer.analyze(records, periods)
        profiles = self.counterparty_analyzer.build_profiles(records, periods)
        cp_patterns = self.counterparty_analyzer.detect_recurring_patterns(records, periods)
        dq_patterns = self.dq_analyzer.analyze(records, periods)

        # Summary statistics
        latest_period = periods[-1].period_key if periods else None
        prev_period = periods[-2].period_key if len(periods) >= 2 else None
        current_period_key = target_period or latest_period

        summary = {
            "total_records": len(records),
            "period_count": len(periods),
            "period_type": period_type.value,
            "target_period": current_period_key,
            "rule_pattern_count": len(rule_patterns),
            "counterparty_count": len(profiles),
            "counterparty_patterns": len(cp_patterns),
            "data_quality_patterns": len(dq_patterns),
        }

        if periods:
            latest_metric = next((p for p in periods if p.period_key == current_period_key), periods[-1])
            summary["latest_compliance_rate"] = latest_metric.compliance_rate
            summary["latest_invoices"] = latest_metric.total_invoices
            summary["latest_compliant"] = latest_metric.compliant_count
            summary["latest_needs_review"] = latest_metric.needs_review_count
            summary["latest_non_compliant"] = latest_metric.non_compliant_count

        evidence = {
            "source": "UC15_HISTORICAL_INTELLIGENCE_ENGINE",
            "evaluated_invoice_ids": [r.invoice_id for r in records],
            "rule_patterns_summary": [
                {"rule_id": p.rule_id, "classification": p.classification.value, "count": p.total_failures}
                for p in rule_patterns[:5]
            ],
            "top_counterparty_patterns": [
                {"counterparty": cp.counterparty_name, "issue": cp.issue_type, "count": cp.occurrences}
                for cp in cp_patterns[:3]
            ],
        }

        report = HistoricalReport(
            report_id=f"HIST-{uuid.uuid4().hex[:8].upper()}",
            period_type=period_type,
            analysis_period=current_period_key,
            previous_period=prev_period,
            total_invoices_analyzed=len(records),
            total_periods_covered=len(periods),
            periods=periods,
            trends=trends,
            rule_patterns=rule_patterns,
            counterparty_profiles=profiles,
            counterparty_patterns=cp_patterns,
            data_quality_patterns=dq_patterns,
            audit_results=[],
            summary=summary,
            evidence=evidence,
        )
        return report
