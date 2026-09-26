"""
UC15 GST Compliance Agent — Anomaly Intelligence Unit Test Suite (Sprint 7)
Verifies:
  1. Value Anomaly Detection (high/low amount relative to baseline)
  2. Tax Rate Anomaly Detection (deviations from statutory schedules)
  3. Frequency Anomaly Detection (burst transactions on same date)
  4. Hierarchical Baseline Selection (Counterparty -> HSN -> Portfolio -> Insufficient)
  5. Minimum Sample Size Enforcement (insufficient baseline status without false alerts)
  6. Zero Variance Edge Cases (MAD == 0 and IQR == 0 handling)
  7. Multi-Dimensional Anomalies and Canonical Findings Emission
"""
import unittest
from datetime import date
from decimal import Decimal
from typing import List

from app.domain.models.invoice import Invoice
from app.intelligence.anomaly.detectors import (
    AnomalyBaselineRepository,
    FrequencyAnomalyDetector,
    TaxRateAnomalyDetector,
    ValueAnomalyDetector,
)
from app.intelligence.anomaly.engine import AnomalyIntelligenceEngine
from app.intelligence.anomaly.features import InvoiceFeature, InvoiceFeatureExtractor
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
    IntelligenceCategory,
    IntelligenceConfidence,
)
from app.intelligence.config.intelligence_config import AnomalyPolicyConfig
from tests.fixtures.sample_invoices import make_test_invoice


class TestAnomalyStatistics(unittest.TestCase):
    """Test deterministic statistical calculation routines."""

    def test_median_and_mad(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        med = calculate_median(vals)
        self.assertEqual(med, 30.0)
        mad = calculate_mad(vals, med)
        self.assertEqual(mad, 10.0)

    def test_iqr(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        q1, q3, iqr = calculate_iqr(vals)
        self.assertEqual(q1, 3.0)
        self.assertEqual(q3, 7.0)
        self.assertEqual(iqr, 4.0)

    def test_zero_variance_guard(self):
        vals = [100.0, 100.0, 100.0, 100.0, 100.0]
        med = calculate_median(vals)
        mad = calculate_mad(vals, med)
        self.assertEqual(mad, 0.0)
        q1, q3, iqr = calculate_iqr(vals)
        self.assertEqual(iqr, 0.0)

        # Zero variance: identical value should have z-score 0.0 and not raise error
        z = robust_z_score(100.0, med, mad, values_fallback=vals)
        self.assertEqual(z, 0.0)

        is_outlier, lower, upper = iqr_outlier_check(100.0, q1, q3, iqr)
        self.assertFalse(is_outlier)


class TestValueAnomalyDetector(unittest.TestCase):
    """Test Value Anomaly detection logic and boundaries."""

    def setUp(self):
        self.config = AnomalyPolicyConfig()
        self.detector = ValueAnomalyDetector(config=self.config)
        self.repo = AnomalyBaselineRepository()

    def test_high_value_anomaly(self):
        # Baseline: 5 invoices around 10,000 INR
        hist = [
            make_test_invoice(invoice_id=f"HIST-{i}", taxable_value=10000.0 + (i * 100), gstin="27AAACB1234A1Z5")
            for i in range(5)
        ]
        features = InvoiceFeatureExtractor.extract_batch(hist)
        self.repo.ingest_features(features)

        # Extreme transaction: 500,000 INR (50x baseline)
        extreme_inv = make_test_invoice(invoice_id="INV-EXTREME", taxable_value=500000.0, gstin="27AAACB1234A1Z5")
        feat = InvoiceFeatureExtractor.extract(extreme_inv)

        finding = self.detector.evaluate(feat, self.repo)
        self.assertEqual(finding.dimension, AnomalyDimension.VALUE_ANOMALY)
        self.assertEqual(finding.status, AnomalyStatus.ANOMALOUS)
        self.assertIn(finding.level, [AnomalyLevel.HIGH, AnomalyLevel.CRITICAL])
        self.assertGreaterEqual(finding.score, 75.0)
        self.assertIn("exceeds the upper historical boundary", finding.evidence["explanation"])

    def test_normal_value_within_baseline(self):
        hist = [
            make_test_invoice(invoice_id=f"HIST-{i}", taxable_value=10000.0 + (i * 500), gstin="27AAACB1234A1Z5")
            for i in range(5)
        ]
        features = InvoiceFeatureExtractor.extract_batch(hist)
        self.repo.ingest_features(features)

        normal_inv = make_test_invoice(invoice_id="INV-NORM", taxable_value=11000.0, gstin="27AAACB1234A1Z5")
        feat = InvoiceFeatureExtractor.extract(normal_inv)

        finding = self.detector.evaluate(feat, self.repo)
        self.assertEqual(finding.status, AnomalyStatus.NORMAL)
        self.assertEqual(finding.level, AnomalyLevel.LOW)

    def test_zero_or_missing_value(self):
        inv = make_test_invoice(invoice_id="INV-ZERO", taxable_value=0.0)
        feat = InvoiceFeatureExtractor.extract(inv)
        finding = self.detector.evaluate(feat, self.repo)
        self.assertEqual(finding.status, AnomalyStatus.NOT_EVALUATED)


class TestTaxRateAnomalyDetector(unittest.TestCase):
    """Test tax rate anomaly evaluation against statutory schedule."""

    def setUp(self):
        self.detector = TaxRateAnomalyDetector()
        self.repo = AnomalyBaselineRepository()

    def test_non_statutory_tax_rate_anomaly(self):
        # Effective tax rate 15.0% (not in standard 0%, 5%, 12%, 18%, 28%)
        inv = make_test_invoice(
            invoice_id="INV-ODD-RATE",
            taxable_value=10000.0,
            cgst_rate=7.5,
            sgst_rate=7.5,
            igst_rate=0.0,
            total_amt=11500.0,
        )
        feat = InvoiceFeatureExtractor.extract(inv)
        finding = self.detector.evaluate(feat, self.repo)
        self.assertEqual(finding.dimension, AnomalyDimension.TAX_RATE_ANOMALY)
        self.assertEqual(finding.status, AnomalyStatus.ANOMALOUS)
        self.assertIn(finding.level, [AnomalyLevel.HIGH, AnomalyLevel.CRITICAL])
        self.assertIn("does not align with standard statutory GST rate slabs", finding.evidence["explanation"])

    def test_statutory_tax_rate_normal(self):
        inv = make_test_invoice(
            invoice_id="INV-NORMAL-RATE",
            taxable_value=10000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=11800.0,
        )
        feat = InvoiceFeatureExtractor.extract(inv)
        finding = self.detector.evaluate(feat, self.repo)
        self.assertEqual(finding.status, AnomalyStatus.NORMAL)
        self.assertEqual(finding.level, AnomalyLevel.LOW)


class TestFrequencyAnomalyDetector(unittest.TestCase):
    """Test burst transaction frequency detection."""

    def setUp(self):
        self.detector = FrequencyAnomalyDetector()
        self.repo = AnomalyBaselineRepository()

    def test_burst_same_day_transactions(self):
        # Same counterparty issuing 5 invoices on the exact same date
        burst_invoices = [
            make_test_invoice(
                invoice_id=f"BURST-{i}",
                invoice_date="2026-03-15",
                gstin="27AAACB1234A1Z5",
            )
            for i in range(5)
        ]
        features = InvoiceFeatureExtractor.extract_batch(burst_invoices)
        self.repo.ingest_features(features)

        finding = self.detector.evaluate(features[0], self.repo)
        self.assertEqual(finding.dimension, AnomalyDimension.FREQUENCY_ANOMALY)
        self.assertEqual(finding.status, AnomalyStatus.ANOMALOUS)
        self.assertGreaterEqual(finding.score, 60.0)
        self.assertIn("split billing or transaction surge", finding.evidence["explanation"])

    def test_normal_frequency(self):
        invoices = [
            make_test_invoice(
                invoice_id="NORM-1",
                invoice_date="2026-03-01",
                gstin="27AAACB1234A1Z5",
            ),
            make_test_invoice(
                invoice_id="NORM-2",
                invoice_date="2026-03-15",
                gstin="27AAACB1234A1Z5",
            ),
        ]
        features = InvoiceFeatureExtractor.extract_batch(invoices)
        self.repo.ingest_features(features)

        finding = self.detector.evaluate(features[0], self.repo)
        self.assertEqual(finding.status, AnomalyStatus.NORMAL)


class TestHierarchicalBaselines(unittest.TestCase):
    """Test hierarchical fallback: Counterparty -> HSN -> Portfolio -> Insufficient."""

    def setUp(self):
        self.repo = AnomalyBaselineRepository()
        self.min_obs = {"counterparty": 3, "hsn": 5, "portfolio": 10}

    def test_insufficient_baseline(self):
        # 1 invoice total
        inv = make_test_invoice(gstin="VEND-NEW", hsn_code="8409")
        self.repo.ingest_features(InvoiceFeatureExtractor.extract_batch([inv]))

        dist, scope, n = self.repo.get_value_baseline("VEND-NEW", "8409", self.min_obs)
        self.assertEqual(scope, "INSUFFICIENT")
        self.assertEqual(n, 1)

    def test_counterparty_baseline_preferred(self):
        # 4 invoices for VEND-A (>= 3)
        invs = [make_test_invoice(gstin="VEND-A", hsn_code="8409", taxable_value=1000.0) for _ in range(4)]
        self.repo.ingest_features(InvoiceFeatureExtractor.extract_batch(invs))

        dist, scope, n = self.repo.get_value_baseline("VEND-A", "8409", self.min_obs)
        self.assertEqual(scope, "COUNTERPARTY")
        self.assertEqual(n, 4)

    def test_hsn_fallback_when_counterparty_insufficient(self):
        # VEND-B has only 1 invoice (< 3), but HSN 8409 has 6 invoices (>= 5)
        invs_hsn = [make_test_invoice(gstin=f"VEND-{i}", hsn_code="8409", taxable_value=2000.0) for i in range(6)]
        self.repo.ingest_features(InvoiceFeatureExtractor.extract_batch(invs_hsn))

        dist, scope, n = self.repo.get_value_baseline("VEND-0", "8409", self.min_obs)
        self.assertEqual(scope, "HSN")
        self.assertEqual(n, 6)

    def test_portfolio_fallback(self):
        # Counterparty < 3, HSN < 5, but portfolio >= 10
        invs = [make_test_invoice(gstin=f"VEND-{i}", hsn_code=f"HSN-{i}", taxable_value=3000.0) for i in range(12)]
        self.repo.ingest_features(InvoiceFeatureExtractor.extract_batch(invs))

        dist, scope, n = self.repo.get_value_baseline("VEND-0", "HSN-0", self.min_obs)
        self.assertEqual(scope, "PORTFOLIO")
        self.assertEqual(n, 12)


class TestAnomalyEngineIntegration(unittest.TestCase):
    """Test full multi-dimensional Anomaly Engine execution and Canonical Findings."""

    def test_multi_dimensional_anomaly_emission(self):
        # Historical baseline of 5 normal invoices
        hist = [
            make_test_invoice(
                invoice_id=f"HIST-{i}",
                taxable_value=10000.0,
                cgst_rate=9.0,
                sgst_rate=9.0,
                total_amt=11800.0,
                gstin="27AAACB1234A1Z5",
            )
            for i in range(5)
        ]

        # Target invoice has BOTH an extreme value anomaly AND non-statutory tax rate anomaly
        target_inv = make_test_invoice(
            invoice_id="INV-COMBO-ANOM",
            taxable_value=500000.0,  # 50x baseline
            cgst_rate=7.0,          # 14% total tax (non-statutory)
            sgst_rate=7.0,
            total_amt=570000.0,
            gstin="27AAACB1234A1Z5",
        )

        engine = AnomalyIntelligenceEngine()
        anomaly_findings, intel_findings = engine.analyze(
            invoices=[target_inv],
            historical_invoices=hist,
        )

        # 3 dimensional findings evaluated (Value, Tax Rate, Frequency)
        self.assertEqual(len(anomaly_findings), 3)

        # Value and Tax Rate both flagged ANOMALOUS
        anom_dims = {af.dimension for af in anomaly_findings if af.status == AnomalyStatus.ANOMALOUS}
        self.assertIn(AnomalyDimension.VALUE_ANOMALY, anom_dims)
        self.assertIn(AnomalyDimension.TAX_RATE_ANOMALY, anom_dims)

        # Intelligence findings emitted for the anomalous dimensions
        self.assertGreaterEqual(len(intel_findings), 2)
        for f in intel_findings:
            self.assertEqual(f.category, IntelligenceCategory.ANOMALY)
            self.assertEqual(f.invoice_id, "INV-COMBO-ANOM")
            self.assertIn("detector", f.to_dict())


if __name__ == "__main__":
    unittest.main()
