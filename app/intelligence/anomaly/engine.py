"""
app.intelligence.anomaly.engine
===============================
Anomaly Intelligence Engine orchestrating feature extraction, hierarchical baselining,
dimensional evaluation, and transformation into canonical IntelligenceFinding records.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.domain.models.invoice import Invoice
from app.intelligence.anomaly.detectors import (
    AnomalyBaselineRepository,
    FrequencyAnomalyDetector,
    TaxRateAnomalyDetector,
    ValueAnomalyDetector,
)
from app.intelligence.anomaly.features import InvoiceFeature, InvoiceFeatureExtractor
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.common.enums import (
    AnomalyDimension,
    AnomalyStatus,
    IntelligenceCategory,
)
from app.intelligence.common.models import IntelligenceFinding
from app.intelligence.config.intelligence_config import (
    AnomalyPolicyConfig,
    default_intelligence_config,
)


class AnomalyIntelligenceEngine:
    """
    Central engine for Anomaly Intelligence.
    Maintains baseline repository, executes dimensional detectors, and emits canonical findings.
    """
    ENGINE_NAME = "ANOMALY_INTELLIGENCE_ENGINE"
    ENGINE_VERSION = "1.0"

    def __init__(self, config: Optional[AnomalyPolicyConfig] = None) -> None:
        self.config = config or default_intelligence_config.anomaly
        self.baseline_repo = AnomalyBaselineRepository()
        self.value_detector = ValueAnomalyDetector(config=self.config)
        self.tax_detector = TaxRateAnomalyDetector(config=self.config)
        self.frequency_detector = FrequencyAnomalyDetector(config=self.config)

    def analyze(
        self,
        invoices: List[Invoice],
        historical_invoices: Optional[List[Invoice]] = None,
    ) -> Tuple[List[AnomalyFinding], List[IntelligenceFinding]]:
        """
        Analyze a batch of invoices against historical and current batch baselines.
        Returns:
            - anomaly_findings: All dimensional findings (Value, Tax Rate, Frequency).
            - intelligence_findings: Canonical findings for anomalous or insufficient baseline events.
        """
        if not invoices:
            return [], []

        # 1. Extract feature vectors
        current_features = InvoiceFeatureExtractor.extract_batch(invoices)
        historical_features = InvoiceFeatureExtractor.extract_batch(historical_invoices or [])

        # 2. Populate baseline repository with historical + current data
        all_features = historical_features + current_features
        self.baseline_repo.ingest_features(all_features)

        anomaly_findings: List[AnomalyFinding] = []
        intelligence_findings: List[IntelligenceFinding] = []

        # 3. Evaluate each invoice across all anomaly dimensions
        for feat in current_features:
            v_finding = self.value_detector.evaluate(feat, self.baseline_repo)
            t_finding = self.tax_detector.evaluate(feat, self.baseline_repo)
            f_finding = self.frequency_detector.evaluate(feat, self.baseline_repo)

            all_dim_findings = [v_finding, t_finding, f_finding]
            anomaly_findings.extend(all_dim_findings)

            # Transform ANOMALOUS findings into canonical IntelligenceFindings
            for af in all_dim_findings:
                if af.status == AnomalyStatus.ANOMALOUS:
                    title = f"Statistical Anomaly: {af.dimension.value} on {af.invoice_id}"
                    desc = af.evidence.get("explanation", f"Anomalous transaction detected on {af.dimension.value}.")

                    finding = IntelligenceFinding(
                        finding_id=f"FIND-ANOM-{uuid.uuid4().hex[:8].upper()}",
                        invoice_id=af.invoice_id,
                        category=IntelligenceCategory.ANOMALY,
                        finding_type=af.dimension.value,
                        status=af.status.value,
                        score=af.score,
                        confidence=af.confidence,
                        severity=af.level.value,
                        title=title,
                        description=desc,
                        evidence=af.evidence,
                        related_invoice_ids=[],
                        detector=f"{af.dimension.value}_DETECTOR",
                        detector_version=self.ENGINE_VERSION,
                        source_lineage={
                            "invoice_id": af.invoice_id,
                            "baseline_scope": af.baseline_scope,
                            "baseline_sample_size": af.baseline_sample_size,
                            "observed_value": af.observed_value,
                        },
                    )
                    intelligence_findings.append(finding)

        return anomaly_findings, intelligence_findings
