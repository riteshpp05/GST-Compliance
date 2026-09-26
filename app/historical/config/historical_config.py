"""
UC15 GST Compliance Agent — Historical Intelligence Configuration
Defines transparent, configurable, deterministic thresholds for time-series trend analysis,
rule failure pattern classification, counterparty profiling, and data-quality tracking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class HistoricalConfig:
    """
    Configurable parameters for historical pattern recognition and trend analysis.
    Eliminates arbitrary heuristic or AI guesswork through clear statutory & mathematical rules.
    """
    # -------------------------------------------------------------------------
    # Trend Analysis Thresholds (Period-over-Period)
    # -------------------------------------------------------------------------
    # Absolute change in percentage points to declare improving/deteriorating trend
    trend_improving_threshold_pp: float = 5.0      # >= +5.0 pp -> IMPROVING
    trend_deteriorating_threshold_pp: float = -5.0  # <= -5.0 pp -> DETERIORATING
    # Minimum invoice volume in a period to calculate a statistically meaningful trend
    min_period_invoices_for_trend: int = 1

    # -------------------------------------------------------------------------
    # Rule Failure Pattern Classification Thresholds
    # -------------------------------------------------------------------------
    # Minimum total failure occurrences across periods to constitute a recurring pattern
    min_pattern_invoices: int = 2
    # Minimum distinct time periods with failures to establish recurrence
    min_pattern_periods: int = 2
    # Number of consecutive periods with failures to classify as PERSISTENT
    persistent_consecutive_periods: int = 2
    # Failure growth factor in latest period compared to historical baseline to classify as EMERGING
    emerging_growth_factor: float = 1.5
    # Minimum absolute failure count in latest period to classify as EMERGING
    emerging_min_latest_failures: int = 2
    # Proportion decrease in failure count or rate to classify as IMPROVING
    improving_reduction_ratio: float = 0.25

    # -------------------------------------------------------------------------
    # Counterparty Intelligence Thresholds
    # -------------------------------------------------------------------------
    # Minimum total invoices from a counterparty to form a historical profile
    counterparty_min_invoices: int = 1
    # Minimum failures from counterparty on same rule/issue to flag recurring pattern
    counterparty_recurring_min_failures: int = 2
    # Threshold percentage of non-compliance to highlight high-risk counterparty
    counterparty_high_failure_rate_pct: float = 30.0

    # -------------------------------------------------------------------------
    # Data Quality History Thresholds
    # -------------------------------------------------------------------------
    # Minimum occurrences of a data quality finding to classify as recurring DQ pattern
    dq_min_occurrences: int = 2
    # Proportion of counterparty invoices affected by DQ to flag systematic DQ issue
    dq_counterparty_affected_ratio: float = 0.20

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# Default singleton configuration
default_historical_config = HistoricalConfig()
