"""
UC15 GST Compliance Agent — Time Period Analyzer (Sprint 5)
Provides deterministic time-series aggregation across Daily, Weekly, Monthly, and Quarterly intervals.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from app.historical.models.period import PeriodMetrics, PeriodType
from app.historical.models.record import HistoricalRecord


class PeriodAnalyzer:
    """
    Deterministic time-series aggregator converting invoice transactions into structured period metrics.
    """

    @staticmethod
    def get_period_key(d: Optional[date], period_type: PeriodType) -> str:
        """Derive standard deterministic period key for a given date."""
        if d is None:
            d = date(2023, 1, 1)
        if period_type == PeriodType.DAILY:
            return d.strftime("%Y-%m-%d")
        elif period_type == PeriodType.WEEKLY:
            iso_year, iso_week, _ = d.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif period_type == PeriodType.QUARTERLY:
            quarter = (d.month - 1) // 3 + 1
            return f"{d.year}-Q{quarter}"
        else:  # MONTHLY (default)
            return d.strftime("%Y-%m")

    @staticmethod
    def get_period_bounds(period_key: str, period_type: PeriodType) -> Tuple[date, date]:
        """Compute inclusive start and end dates for a period key."""
        if period_type == PeriodType.DAILY:
            d = date.fromisoformat(period_key)
            return d, d

        elif period_type == PeriodType.WEEKLY:
            parts = period_key.split("-W")
            year = int(parts[0])
            week = int(parts[1])
            # Monday of the ISO week
            start = date.fromisocalendar(year, week, 1)
            end = date.fromisocalendar(year, week, 7)
            return start, end

        elif period_type == PeriodType.QUARTERLY:
            parts = period_key.split("-Q")
            year = int(parts[0])
            quarter = int(parts[1])
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            start = date(year, start_month, 1)
            last_day = calendar.monthrange(year, end_month)[1]
            end = date(year, end_month, last_day)
            return start, end

        else:  # MONTHLY
            parts = period_key.split("-")
            year = int(parts[0])
            month = int(parts[1])
            start = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            end = date(year, month, last_day)
            return start, end

    def aggregate(
        self,
        records: List[HistoricalRecord],
        period_type: PeriodType = PeriodType.MONTHLY,
    ) -> List[PeriodMetrics]:
        """
        Group records by period and compute deterministic compliance & financial metrics.
        Returns chronologically sorted list of PeriodMetrics.
        """
        if not records:
            return []

        # Bucket records by period_key
        buckets: Dict[str, List[HistoricalRecord]] = defaultdict(list)
        for rec in records:
            inv_d = rec.invoice_date or date(2023, 1, 1)
            pkey = self.get_period_key(inv_d, period_type)
            buckets[pkey].append(rec)

        results: List[PeriodMetrics] = []

        # Sort period keys chronologically
        for pkey in sorted(buckets.keys()):
            recs = buckets[pkey]
            start_d, end_d = self.get_period_bounds(pkey, period_type)

            metric = PeriodMetrics(
                period_key=pkey,
                period_type=period_type,
                start_date=start_d,
                end_date=end_d,
                total_invoices=len(recs),
            )

            total_taxable = Decimal("0.00")
            total_tax = Decimal("0.00")
            total_amount = Decimal("0.00")
            failed_gates_sum = 0
            rule_failures: Dict[str, int] = defaultdict(int)
            gate_failures: Dict[int, int] = defaultdict(int)

            for r in recs:
                metric.invoices.append(r.invoice_id)
                status = (r.compliance_status or "").upper()
                if status == "COMPLIANT":
                    metric.compliant_count += 1
                elif status == "NEEDS_REVIEW":
                    metric.needs_review_count += 1
                else:
                    metric.non_compliant_count += 1

                total_taxable += r.taxable_value
                total_tax += r.total_tax
                total_amount += r.total_amount
                failed_gates_sum += r.failed_gate_count

                for rid in r.failed_rule_ids:
                    rule_failures[rid] += 1
                for gno in r.failed_gate_numbers:
                    gate_failures[gno] += 1

            metric.total_taxable_value = total_taxable
            metric.total_tax = total_tax
            metric.total_amount = total_amount
            metric.failed_gate_count = failed_gates_sum
            metric.rule_failure_counts = dict(rule_failures)
            metric.gate_failure_counts = dict(gate_failures)
            metric.calculate_rates()

            results.append(metric)

        return results
