"""
UC15 GST Compliance Agent — Rule Failure Pattern Analyzer (Sprint 5)
Provides deterministic detection and classification of recurring statutory rule failures over time.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from app.historical.config.historical_config import HistoricalConfig, default_historical_config
from app.historical.models.pattern import RuleFailurePattern, RulePatternClassification
from app.historical.models.period import PeriodMetrics
from app.historical.models.record import HistoricalRecord


class RulePatternAnalyzer:
    """
    Analyzes statutory rule failures across chronological periods to identify
    persistent, emerging, improving, resolved, and isolated failure patterns.
    """

    def __init__(self, config: Optional[HistoricalConfig] = None) -> None:
        self.config = config or default_historical_config

    def analyze(
        self,
        records: List[HistoricalRecord],
        periods: List[PeriodMetrics],
    ) -> List[RuleFailurePattern]:
        """
        Scan all records and periods to classify rule failure trajectories.
        """
        if not records or not periods:
            return []

        # 1. Map all rule failures: rule_id -> period_key -> list of invoice_ids
        rule_period_invoices: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        rule_categories: Dict[str, str] = {}

        for r in records:
            pkey = None
            # Find period key for invoice_date
            for p in periods:
                if p.start_date <= r.invoice_date <= p.end_date:
                    pkey = p.period_key
                    break
            if not pkey:
                continue

            for rid in r.failed_rule_ids:
                rule_period_invoices[rid][pkey].append(r.invoice_id)
                # Infer category from gate results if present
                if rid in r.gate_results and not rule_categories.get(rid):
                    rule_categories[rid] = r.gate_results[rid].get("category", "STATUTORY")

        period_keys = [p.period_key for p in periods]
        latest_period_key = period_keys[-1] if period_keys else ""
        latest_period_obj = periods[-1] if periods else None
        latest_total_inv = latest_period_obj.total_invoices if latest_period_obj else 1

        patterns: List[RuleFailurePattern] = []

        for rule_id, period_map in sorted(rule_period_invoices.items()):
            # Aggregate totals
            all_affected: Set[str] = set()
            period_counts: Dict[str, int] = {}
            periods_with_failures: List[str] = []

            for pkey in period_keys:
                cnt = len(period_map.get(pkey, []))
                period_counts[pkey] = cnt
                if cnt > 0:
                    periods_with_failures.append(pkey)
                    all_affected.update(period_map[pkey])

            total_failures = sum(period_counts.values())
            affected_count = len(all_affected)

            if total_failures == 0:
                continue

            first_seen = periods_with_failures[0]
            last_seen = periods_with_failures[-1]
            latest_count = period_counts.get(latest_period_key, 0)
            latest_rate = round((latest_count / latest_total_inv) * 100.0, 2) if latest_total_inv > 0 else 0.0

            # 2. Classification Logic
            classification = self._classify(
                period_keys=period_keys,
                period_counts=period_counts,
                periods_with_failures=periods_with_failures,
                total_failures=total_failures,
            )

            # 3. Formulate Deterministic Evidence & Description
            evidence = {
                "rule_id": rule_id,
                "classification": classification.value,
                "total_failures": total_failures,
                "affected_invoice_count": affected_count,
                "periods_with_failures": periods_with_failures,
                "period_counts": period_counts,
                "latest_period": latest_period_key,
                "latest_count": latest_count,
            }

            trend_desc = self._build_description(
                rule_id=rule_id,
                classification=classification,
                period_counts=period_counts,
                periods_with_failures=periods_with_failures,
                total_failures=total_failures,
            )

            pattern = RuleFailurePattern(
                pattern_id=f"PAT-RULE-{rule_id}",
                rule_id=rule_id,
                rule_category=rule_categories.get(rule_id, "STATUTORY"),
                classification=classification,
                total_failures=total_failures,
                affected_invoice_count=affected_count,
                affected_invoices=sorted(list(all_affected)),
                first_seen_period=first_seen,
                last_seen_period=last_seen,
                periods_observed=periods_with_failures,
                period_counts=period_counts,
                latest_period=latest_period_key,
                latest_failure_count=latest_count,
                latest_failure_rate=latest_rate,
                trend_description=trend_desc,
                evidence=evidence,
            )
            patterns.append(pattern)

        # Sort patterns: PERSISTENT first, then EMERGING, IMPROVING, RESOLVED, ISOLATED, then by total failures desc
        order = {
            RulePatternClassification.PERSISTENT: 1,
            RulePatternClassification.EMERGING: 2,
            RulePatternClassification.IMPROVING: 3,
            RulePatternClassification.RESOLVED: 4,
            RulePatternClassification.ISOLATED: 5,
        }
        return sorted(patterns, key=lambda p: (order.get(p.classification, 99), -p.total_failures))

    def _classify(
        self,
        period_keys: List[str],
        period_counts: Dict[str, int],
        periods_with_failures: List[str],
        total_failures: int,
    ) -> RulePatternClassification:
        """
        Classify rule failure trajectory based on transparent configurable thresholds.
        """
        if len(period_keys) < 2:
            if total_failures >= self.config.min_pattern_invoices:
                return RulePatternClassification.PERSISTENT
            return RulePatternClassification.ISOLATED

        latest_key = period_keys[-1]
        prev_key = period_keys[-2]
        latest_cnt = period_counts.get(latest_key, 0)
        prev_cnt = period_counts.get(prev_key, 0)

        # 1. RESOLVED: Was failing in prior periods, but exactly 0 in the latest period
        if latest_cnt == 0 and len(periods_with_failures) >= 1 and periods_with_failures[-1] != latest_key:
            # Must have had meaningful prior failures
            if sum(period_counts[k] for k in period_keys[:-1]) >= self.config.min_pattern_invoices:
                return RulePatternClassification.RESOLVED

        # 2. EMERGING: Low or 0 earlier, but surged significantly in latest period
        prior_counts = [period_counts[k] for k in period_keys[:-1]]
        avg_prior = sum(prior_counts) / len(prior_counts) if prior_counts else 0.0
        if latest_cnt >= self.config.emerging_min_latest_failures:
            if avg_prior == 0 or (latest_cnt >= avg_prior * self.config.emerging_growth_factor):
                # Also check if latest count grew significantly over previous
                if prev_cnt == 0 or latest_cnt >= prev_cnt * self.config.emerging_growth_factor:
                    return RulePatternClassification.EMERGING

        # 3. IMPROVING: Failure count consistently decreasing
        if len(period_keys) >= 2 and latest_cnt < prev_cnt and latest_cnt > 0:
            reduction = (prev_cnt - latest_cnt) / prev_cnt
            if reduction >= self.config.improving_reduction_ratio:
                return RulePatternClassification.IMPROVING

        # 4. PERSISTENT: Fails across consecutive periods (>= persistent_consecutive_periods)
        consecutive = 0
        max_consecutive = 0
        for pkey in period_keys:
            if period_counts.get(pkey, 0) > 0:
                consecutive += 1
                if consecutive > max_consecutive:
                    max_consecutive = consecutive
            else:
                consecutive = 0

        if max_consecutive >= self.config.persistent_consecutive_periods and total_failures >= self.config.min_pattern_invoices:
            return RulePatternClassification.PERSISTENT

        # Default to ISOLATED if recurrence criteria not met
        return RulePatternClassification.ISOLATED

    def _build_description(
        self,
        rule_id: str,
        classification: RulePatternClassification,
        period_counts: Dict[str, int],
        periods_with_failures: List[str],
        total_failures: int,
    ) -> str:
        seq = " -> ".join(f"{k}: {period_counts[k]}" for k in sorted(period_counts.keys()))
        if classification == RulePatternClassification.PERSISTENT:
            return f"Rule {rule_id} exhibited persistent statutory failures across {len(periods_with_failures)} periods ({seq}), totaling {total_failures} failures."
        elif classification == RulePatternClassification.EMERGING:
            return f"Rule {rule_id} emerged as a new high-frequency issue in the latest period ({seq}), totaling {total_failures} failures."
        elif classification == RulePatternClassification.IMPROVING:
            return f"Rule {rule_id} showed an improving failure trend with declining occurrences in recent periods ({seq})."
        elif classification == RulePatternClassification.RESOLVED:
            return f"Rule {rule_id} is resolved in the latest period with 0 failures after previous non-compliance ({seq})."
        else:
            return f"Rule {rule_id} exhibited isolated/sporadic failures ({seq}), totaling {total_failures} failures."
