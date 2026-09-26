"""
UC15 GST Compliance Agent — Counterparty Historical Intelligence Analyzer (Sprint 5)
Provides counterparty compliance profiling and recurring consistency pattern detection.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.historical.config.historical_config import HistoricalConfig, default_historical_config
from app.historical.models.counterparty import CounterpartyProfile, RecurringCounterpartyPattern
from app.historical.models.period import PeriodMetrics
from app.historical.models.record import HistoricalRecord
from app.historical.models.trend import TrendDirection


class CounterpartyAnalyzer:
    """
    Constructs historical profiles for vendors and customers and flags systemic recurring non-compliance.
    """

    def __init__(self, config: Optional[HistoricalConfig] = None) -> None:
        self.config = config or default_historical_config

    def build_profiles(
        self,
        records: List[HistoricalRecord],
        periods: List[PeriodMetrics],
    ) -> List[CounterpartyProfile]:
        """
        Aggregate compliance history per counterparty (vendor / customer).
        """
        if not records:
            return []

        # Group records by counterparty identifier
        groups: Dict[str, List[HistoricalRecord]] = defaultdict(list)
        for r in records:
            c_id = r.counterparty_gstin or r.counterparty_name or "UNKNOWN_COUNTERPARTY"
            groups[c_id.strip()].append(r)

        profiles: List[CounterpartyProfile] = []

        for c_id, recs in groups.items():
            recs_sorted = sorted(recs, key=lambda x: (x.invoice_date, x.invoice_id))
            first_r = recs_sorted[0]
            last_r = recs_sorted[-1]

            name = first_r.counterparty_name or c_id
            gstin = first_r.counterparty_gstin or ""
            direction = first_r.direction

            compliant = 0
            needs_review = 0
            non_compliant = 0
            rule_fail_counts: Dict[str, int] = defaultdict(int)
            periods_active: set[str] = set()
            affected_invs: List[str] = []

            for r in recs_sorted:
                affected_invs.append(r.invoice_id)
                st = (r.compliance_status or "").upper()
                if st == "COMPLIANT":
                    compliant += 1
                elif st == "NEEDS_REVIEW":
                    needs_review += 1
                else:
                    non_compliant += 1

                for rid in r.failed_rule_ids:
                    rule_fail_counts[rid] += 1

                # Locate period
                for p in periods:
                    if p.start_date <= r.invoice_date <= p.end_date:
                        periods_active.add(p.period_key)
                        break

            # Top failed rules
            top_rules = sorted(rule_fail_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            total_failures = sum(rule_fail_counts.values())

            profile = CounterpartyProfile(
                counterparty_id=c_id,
                counterparty_name=name,
                gstin=gstin,
                direction=direction,
                total_invoices=len(recs),
                compliant_count=compliant,
                needs_review_count=needs_review,
                non_compliant_count=non_compliant,
                total_failures=total_failures,
                top_failed_rules=top_rules,
                first_transaction_date=first_r.invoice_date,
                last_transaction_date=last_r.invoice_date,
                periods_active=sorted(list(periods_active)),
                affected_invoices=affected_invs,
            )
            profile.calculate_rate()

            # Determine simple recent trend if active across multiple periods
            if len(profile.periods_active) >= 2:
                recent_p = profile.periods_active[-1]
                prev_p = profile.periods_active[-2]
                rec_recent = [r for r in recs if self._matches_period(r, recent_p, periods)]
                rec_prev = [r for r in recs if self._matches_period(r, prev_p, periods)]
                if rec_recent and rec_prev:
                    rate_recent = (sum(1 for r in rec_recent if r.compliance_status == "COMPLIANT") / len(rec_recent)) * 100.0
                    rate_prev = (sum(1 for r in rec_prev if r.compliance_status == "COMPLIANT") / len(rec_prev)) * 100.0
                    delta = rate_recent - rate_prev
                    if delta >= self.config.trend_improving_threshold_pp:
                        profile.recent_trend = TrendDirection.IMPROVING
                    elif delta <= self.config.trend_deteriorating_threshold_pp:
                        profile.recent_trend = TrendDirection.DETERIORATING
                    else:
                        profile.recent_trend = TrendDirection.STABLE

            profiles.append(profile)

        # Sort by total invoices desc, then compliance_rate asc
        return sorted(profiles, key=lambda p: (-p.total_invoices, p.compliance_rate))

    def detect_recurring_patterns(
        self,
        records: List[HistoricalRecord],
        periods: List[PeriodMetrics],
    ) -> List[RecurringCounterpartyPattern]:
        """
        Identify recurring systemic anomalies from a counterparty across multiple periods.
        Example: Same vendor consistently applying wrong rate on same HSN across periods.
        """
        if not records:
            return []

        patterns: List[RecurringCounterpartyPattern] = []

        # 1. Group records by (counterparty_id, hsn_code, failed_rule_id)
        anomaly_groups: Dict[Tuple[str, str, str], List[HistoricalRecord]] = defaultdict(list)

        for r in records:
            c_id = r.counterparty_gstin or r.counterparty_name or "UNKNOWN"
            hsn = r.hsn_code or "NONE"
            for rid in r.failed_rule_ids:
                anomaly_groups[(c_id.strip(), hsn, rid)].append(r)

        for (c_id, hsn, rid), group in sorted(anomaly_groups.items()):
            if len(group) < self.config.counterparty_recurring_min_failures:
                continue

            # Identify periods observed
            periods_seen: set[str] = set()
            for r in group:
                for p in periods:
                    if p.start_date <= r.invoice_date <= p.end_date:
                        periods_seen.add(p.period_key)
                        break

            # Require multi-period or high volume
            if len(periods_seen) >= 1 and len(group) >= self.config.counterparty_recurring_min_failures:
                first_r = group[0]
                name = first_r.counterparty_name or c_id
                gate_info = first_r.gate_results.get(rid, {})

                issue_type = "RECURRING_RULE_FAILURE"
                if "tax" in rid.lower():
                    issue_type = "RECURRING_TAX_RATE_MISMATCH"
                elif "hsn" in rid.lower():
                    issue_type = "RECURRING_HSN_DEFECT"
                elif "pos" in rid.lower():
                    issue_type = "RECURRING_POS_MISMATCH"
                elif "itc" in rid.lower():
                    issue_type = "RECURRING_BLOCKED_ITC"

                expected = gate_info.get("expected_value")
                actual = gate_info.get("actual_value")

                ev = (
                    f"Counterparty '{name}' ({c_id}) exhibited {len(group)} repeated {issue_type} "
                    f"under rule '{rid}' (HSN: {hsn}) across {len(periods_seen)} period(s) "
                    f"({', '.join(sorted(periods_seen))})."
                )

                pattern = RecurringCounterpartyPattern(
                    pattern_id=f"PAT-CP-{c_id[:10]}-{hsn}-{rid}",
                    counterparty_id=c_id,
                    counterparty_name=name,
                    pattern_type="RECURRING_COUNTERPARTY_PATTERN",
                    issue_type=issue_type,
                    hsn_code=hsn if hsn != "NONE" else None,
                    rule_id=rid,
                    expected_value=expected,
                    applied_value=actual,
                    occurrences=len(group),
                    periods_observed=sorted(list(periods_seen)),
                    affected_invoices=[r.invoice_id for r in group],
                    evidence=ev,
                )
                patterns.append(pattern)

        return sorted(patterns, key=lambda p: -p.occurrences)

    def _matches_period(self, record: HistoricalRecord, period_key: str, periods: List[PeriodMetrics]) -> bool:
        for p in periods:
            if p.period_key == period_key:
                return p.start_date <= record.invoice_date <= p.end_date
        return False
