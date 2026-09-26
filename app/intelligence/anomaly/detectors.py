"""
app.intelligence.anomaly.detectors
==================================
Deterministic anomaly detectors for Value, Tax Rate, and Transaction Frequency.
Enforces strict baseline hierarchy, sample size gates, and explainable evidence.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.intelligence.anomaly.features import InvoiceFeature
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.anomaly.statistics import (
    calculate_iqr,
    calculate_mad,
    calculate_median,
    iqr_outlier_check,
    robust_z_score,
)
from app.intelligence.common.enums import (
    AnomalyDimension,
    AnomalyLevel,
    AnomalyStatus,
    IntelligenceConfidence,
)
from app.intelligence.config.intelligence_config import (
    AnomalyPolicyConfig,
    default_intelligence_config,
)


class AnomalyBaselineRepository:
    """Aggregates and organizes historical invoice features into hierarchical statistical baselines."""

    def __init__(self) -> None:
        self.counterparty_values: Dict[str, List[float]] = defaultdict(list)
        self.counterparty_rates: Dict[str, List[float]] = defaultdict(list)
        self.counterparty_dates: Dict[str, List[str]] = defaultdict(list)
        self.hsn_values: Dict[str, List[float]] = defaultdict(list)
        self.portfolio_values: List[float] = []
        self.portfolio_rates: List[float] = []

    def ingest_features(self, features: List[InvoiceFeature]) -> None:
        """Add features into baseline distributions."""
        for f in features:
            cid = f.counterparty_id
            val = f.taxable_value
            rate = f.effective_tax_rate
            hsn = f.hsn_code

            if val > 0.0:
                self.counterparty_values[cid].append(val)
                self.portfolio_values.append(val)
                if hsn:
                    self.hsn_values[hsn].append(val)

            if rate >= 0.0:
                self.counterparty_rates[cid].append(rate)
                self.portfolio_rates.append(rate)

            if f.invoice_date:
                self.counterparty_dates[cid].append(f.invoice_date)

    def get_value_baseline(
        self,
        counterparty_id: str,
        hsn_code: str,
        min_obs: Dict[str, int],
    ) -> Tuple[List[float], str, int]:
        """
        Hierarchical baseline selection:
        1. Counterparty-specific (preferred if sample size >= min_obs["counterparty"])
        2. HSN / Category baseline (if sample size >= min_obs["hsn"])
        3. Portfolio baseline (fallback if sample size >= min_obs["portfolio"])
        4. INSUFFICIENT_BASELINE
        """
        # 1. Counterparty
        cp_vals = self.counterparty_values.get(counterparty_id, [])
        if len(cp_vals) >= min_obs.get("counterparty", 3):
            return cp_vals, "COUNTERPARTY", len(cp_vals)

        # 2. HSN
        if hsn_code:
            hsn_vals = self.hsn_values.get(hsn_code, [])
            if len(hsn_vals) >= min_obs.get("hsn", 5):
                return hsn_vals, "HSN", len(hsn_vals)

        # 3. Portfolio
        if len(self.portfolio_values) >= min_obs.get("portfolio", 10):
            return self.portfolio_values, "PORTFOLIO", len(self.portfolio_values)

        # 4. Insufficient
        sample_size = len(cp_vals)
        return cp_vals, "INSUFFICIENT", sample_size


class ValueAnomalyDetector:
    """
    Detects unusually high or low transaction amounts relative to historical baseline.
    Uses Robust Z-Score and IQR boundaries with mandatory sample-size enforcement.
    """
    DETECTOR_NAME = "VALUE_ANOMALY_DETECTOR"
    DETECTOR_VERSION = "1.0"

    def __init__(self, config: Optional[AnomalyPolicyConfig] = None) -> None:
        self.config = config or default_intelligence_config.anomaly

    def evaluate(
        self,
        feature: InvoiceFeature,
        baseline_repo: AnomalyBaselineRepository,
    ) -> AnomalyFinding:
        """Evaluate a single invoice for Value Anomaly."""
        val = feature.taxable_value
        cid = feature.counterparty_id
        hsn = feature.hsn_code

        # Check missing or zero data
        if val <= 0.0:
            return AnomalyFinding(
                invoice_id=feature.invoice_id,
                dimension=AnomalyDimension.VALUE_ANOMALY,
                status=AnomalyStatus.NOT_EVALUATED,
                score=0.0,
                level=AnomalyLevel.LOW,
                confidence=IntelligenceConfidence.LOW,
                baseline_scope="NOT_EVALUATED",
                baseline_sample_size=0,
                observed_value=val,
                evidence={"reason": "Missing or zero taxable value on invoice."},
            )

        # Get baseline
        dist, scope, sample_size = baseline_repo.get_value_baseline(
            counterparty_id=cid,
            hsn_code=hsn,
            min_obs=self.config.minimum_observations,
        )

        min_req = self.config.minimum_observations.get("counterparty", 3)
        if scope == "INSUFFICIENT":
            return AnomalyFinding(
                invoice_id=feature.invoice_id,
                dimension=AnomalyDimension.VALUE_ANOMALY,
                status=AnomalyStatus.INSUFFICIENT_BASELINE,
                score=0.0,
                level=AnomalyLevel.LOW,
                confidence=IntelligenceConfidence.LOW,
                baseline_scope="INSUFFICIENT",
                baseline_sample_size=sample_size,
                observed_value=val,
                evidence={
                    "status": "INSUFFICIENT_BASELINE",
                    "reason": f"Insufficient historical baseline observations (found {sample_size}, minimum required {min_req}).",
                    "counterparty_id": cid,
                },
            )

        # Statistical calculations
        median_val = calculate_median(dist)
        mad_val = calculate_mad(dist, median_val)
        q1, q3, iqr = calculate_iqr(dist)

        robust_z = robust_z_score(val, median_val, mad_val, values_fallback=dist)
        is_outlier, lower_bound, upper_bound = iqr_outlier_check(
            val=val,
            q1=q1,
            q3=q3,
            iqr=iqr,
            multiplier=self.config.iqr.outlier_multiplier,
        )

        # Multiple of median
        median_multiple = round(val / median_val, 2) if median_val > 0.0 else 1.0

        baseline_metrics = {
            "median": round(median_val, 2),
            "mad": round(mad_val, 2),
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2),
            "lower_boundary": lower_bound,
            "upper_boundary": upper_bound,
            "robust_z_score": robust_z,
            "multiple_of_median": median_multiple,
        }

        # Normalization into 0.0 - 100.0 score
        if not is_outlier and robust_z < self.config.robust_z.threshold_medium:
            # Normal transaction
            status = AnomalyStatus.NORMAL
            score = round(min(25.0, robust_z * 8.0), 2)
            level = AnomalyLevel.LOW
            conf = IntelligenceConfidence.HIGH
            evidence = {
                "status": "NORMAL",
                "observed_value": f"INR {val:,.2f}",
                "baseline_median": f"INR {median_val:,.2f}",
                "baseline_scope": scope,
                "sample_size": sample_size,
                "explanation": f"Transaction value of INR {val:,.2f} is consistent with {scope.lower()} baseline median of INR {median_val:,.2f}.",
            }
        else:
            # Anomalous transaction
            status = AnomalyStatus.ANOMALOUS
            # Base score from 60 to 100
            score_calc = 60.0 + min(40.0, (robust_z - 2.5) * 12.0 + max(0.0, median_multiple - 1.5) * 4.0)
            score = round(min(100.0, max(60.0, score_calc)), 2)

            if score >= 85.0 or robust_z >= self.config.robust_z.threshold_critical or median_multiple >= 5.0:
                level = AnomalyLevel.CRITICAL
            elif score >= 75.0 or robust_z >= self.config.robust_z.threshold_high or median_multiple >= 3.0:
                level = AnomalyLevel.HIGH
            else:
                level = AnomalyLevel.MEDIUM

            conf = IntelligenceConfidence.HIGH

            direction_desc = "exceeds the upper historical boundary" if val > upper_bound else "falls significantly below the lower boundary"
            evidence = {
                "status": "ANOMALOUS",
                "observed_value": f"INR {val:,.2f}",
                "baseline_median": f"INR {median_val:,.2f}",
                "baseline_scope": scope,
                "upper_boundary": f"INR {upper_bound:,.2f}",
                "lower_boundary": f"INR {lower_bound:,.2f}",
                "multiple_of_median": f"{median_multiple}x",
                "robust_z_score": robust_z,
                "sample_size": sample_size,
                "explanation": (
                    f"Transaction value of INR {val:,.2f} is approximately {median_multiple}x the "
                    f"{scope.lower()} baseline median (INR {median_val:,.2f}) and {direction_desc} "
                    f"(INR {upper_bound:,.2f})."
                ),
            }

        return AnomalyFinding(
            invoice_id=feature.invoice_id,
            dimension=AnomalyDimension.VALUE_ANOMALY,
            status=status,
            score=score,
            level=level,
            confidence=conf,
            baseline_scope=scope,
            baseline_sample_size=sample_size,
            observed_value=val,
            baseline_metrics=baseline_metrics,
            evidence=evidence,
        )


class TaxRateAnomalyDetector:
    """
    Detects abnormal effective tax rates relative to statutory tax schedules and counterparty history.
    """
    DETECTOR_NAME = "TAX_RATE_ANOMALY_DETECTOR"
    DETECTOR_VERSION = "1.0"

    def __init__(self, config: Optional[AnomalyPolicyConfig] = None) -> None:
        self.config = config or default_intelligence_config.anomaly

    def evaluate(
        self,
        feature: InvoiceFeature,
        baseline_repo: AnomalyBaselineRepository,
    ) -> AnomalyFinding:
        """Evaluate effective tax rate for anomalies."""
        rate = feature.effective_tax_rate
        statutory_rates = self.config.tax_rate.statutory_rates
        tol = self.config.tax_rate.tolerance_pct

        # Check if rate matches any statutory schedule (0%, 5%, 12%, 18%, 28%)
        matches_statutory = any(abs(rate - statutory) <= tol for statutory in statutory_rates)

        if not matches_statutory:
            # Highly unusual non-statutory rate
            status = AnomalyStatus.ANOMALOUS
            score = 80.0
            level = AnomalyLevel.HIGH
            conf = IntelligenceConfidence.HIGH
            evidence = {
                "observed_rate": f"{rate:.2f}%",
                "expected_statutory_rates": statutory_rates,
                "explanation": f"Effective tax rate of {rate:.2f}% does not align with standard statutory GST rate slabs {statutory_rates}.",
            }
        else:
            status = AnomalyStatus.NORMAL
            score = 10.0
            level = AnomalyLevel.LOW
            conf = IntelligenceConfidence.HIGH
            evidence = {
                "observed_rate": f"{rate:.2f}%",
                "explanation": f"Effective tax rate of {rate:.2f}% aligns with statutory GST rate schedule.",
            }

        return AnomalyFinding(
            invoice_id=feature.invoice_id,
            dimension=AnomalyDimension.TAX_RATE_ANOMALY,
            status=status,
            score=score,
            level=level,
            confidence=conf,
            baseline_scope="STATUTORY",
            baseline_sample_size=len(statutory_rates),
            observed_value=rate,
            baseline_metrics={"statutory_rates": statutory_rates},
            evidence=evidence,
        )


class FrequencyAnomalyDetector:
    """
    Detects unusual invoice clustering or transaction velocity surges from a counterparty.
    """
    DETECTOR_NAME = "FREQUENCY_ANOMALY_DETECTOR"
    DETECTOR_VERSION = "1.0"

    def __init__(self, config: Optional[AnomalyPolicyConfig] = None) -> None:
        self.config = config or default_intelligence_config.anomaly

    def evaluate(
        self,
        feature: InvoiceFeature,
        baseline_repo: AnomalyBaselineRepository,
    ) -> AnomalyFinding:
        """Evaluate invoice frequency within the same date window."""
        cid = feature.counterparty_id
        inv_date = feature.invoice_date
        all_dates = baseline_repo.counterparty_dates.get(cid, [])

        same_day_count = sum(1 for d in all_dates if d == inv_date)

        # If a vendor issues 5 or more invoices on the exact same date
        if same_day_count >= 5:
            status = AnomalyStatus.ANOMALOUS
            score = 70.0
            level = AnomalyLevel.MEDIUM
            conf = IntelligenceConfidence.MEDIUM
            evidence = {
                "same_day_invoices_count": same_day_count,
                "invoice_date": inv_date,
                "counterparty_id": cid,
                "explanation": f"Counterparty issued {same_day_count} invoices on the same date ({inv_date}), indicating potential split billing or transaction surge.",
            }
        else:
            status = AnomalyStatus.NORMAL
            score = 5.0
            level = AnomalyLevel.LOW
            conf = IntelligenceConfidence.HIGH
            evidence = {
                "same_day_invoices_count": same_day_count,
                "invoice_date": inv_date,
                "explanation": "Transaction frequency is within normal operational parameters.",
            }

        return AnomalyFinding(
            invoice_id=feature.invoice_id,
            dimension=AnomalyDimension.FREQUENCY_ANOMALY,
            status=status,
            score=score,
            level=level,
            confidence=conf,
            baseline_scope="COUNTERPARTY",
            baseline_sample_size=len(all_dates),
            observed_value=float(same_day_count),
            evidence=evidence,
        )
