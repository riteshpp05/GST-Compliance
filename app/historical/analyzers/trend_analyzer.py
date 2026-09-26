"""
UC15 GST Compliance Agent — Trend Analyzer (Sprint 5)
Provides deterministic period-over-period delta calculation and trend classification.
"""
from __future__ import annotations

from typing import List, Optional

from app.historical.config.historical_config import HistoricalConfig, default_historical_config
from app.historical.models.period import PeriodMetrics
from app.historical.models.trend import PeriodTrend, TrendDirection


class TrendAnalyzer:
    """
    Analyzes historical trajectories across consecutive chronological periods.
    Applies configurable percentage point thresholds to classify trends deterministically.
    """

    def __init__(self, config: Optional[HistoricalConfig] = None) -> None:
        self.config = config or default_historical_config

    def analyze_trends(self, periods: List[PeriodMetrics]) -> List[PeriodTrend]:
        """
        Compute sequential period-over-period compliance trends.
        """
        if not periods:
            return []

        trends: List[PeriodTrend] = []

        for i, curr in enumerate(periods):
            if i == 0:
                # Baseline period (no prior period)
                trend = PeriodTrend(
                    current_period=curr.period_key,
                    previous_period=None,
                    current_compliance_rate=curr.compliance_rate,
                    previous_compliance_rate=None,
                    absolute_change_pp=None,
                    percentage_change=None,
                    direction=TrendDirection.INSUFFICIENT_DATA,
                    current_invoice_count=curr.total_invoices,
                    previous_invoice_count=None,
                    volume_change=None,
                    description=f"Baseline period {curr.period_key}: Compliance rate at {curr.compliance_rate}% across {curr.total_invoices} invoices.",
                )
                trends.append(trend)
                continue

            prev = periods[i - 1]

            # Calculate deltas
            abs_change = round(curr.compliance_rate - prev.compliance_rate, 2)
            pct_change = None
            if prev.compliance_rate > 0:
                pct_change = round(((curr.compliance_rate - prev.compliance_rate) / prev.compliance_rate) * 100.0, 2)

            vol_change = curr.total_invoices - prev.total_invoices

            # Classify direction
            if curr.total_invoices < self.config.min_period_invoices_for_trend or prev.total_invoices < self.config.min_period_invoices_for_trend:
                direction = TrendDirection.INSUFFICIENT_DATA
                desc = f"Insufficient transaction volume in period {curr.period_key} to evaluate statistically reliable trend."
            elif abs_change >= self.config.trend_improving_threshold_pp:
                direction = TrendDirection.IMPROVING
                desc = f"Compliance improved by +{abs_change} percentage points from {prev.compliance_rate}% in {prev.period_key} to {curr.compliance_rate}% in {curr.period_key}."
            elif abs_change <= self.config.trend_deteriorating_threshold_pp:
                direction = TrendDirection.DETERIORATING
                desc = f"Compliance deteriorated by {abs_change} percentage points from {prev.compliance_rate}% in {prev.period_key} to {curr.compliance_rate}% in {curr.period_key}."
            else:
                direction = TrendDirection.STABLE
                desc = f"Compliance remained stable at {curr.compliance_rate}% in {curr.period_key} (delta: {abs_change:+} pp compared to {prev.period_key})."

            trend = PeriodTrend(
                current_period=curr.period_key,
                previous_period=prev.period_key,
                current_compliance_rate=curr.compliance_rate,
                previous_compliance_rate=prev.compliance_rate,
                absolute_change_pp=abs_change,
                percentage_change=pct_change,
                direction=direction,
                current_invoice_count=curr.total_invoices,
                previous_invoice_count=prev.total_invoices,
                volume_change=vol_change,
                description=desc,
            )
            trends.append(trend)

        return trends
