"""
Unit tests for Risk domain models and enums.
"""
import unittest
from datetime import datetime
from decimal import Decimal

from app.domain.enums.confidence_level import ConfidenceLevel
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.risk_priority import RiskPriority
from app.domain.models.risk import (
    BatchRiskReport,
    CategoryRisk,
    RiskAssessment,
    RiskDistribution,
    RiskFactor,
)


class TestRiskDomainModels(unittest.TestCase):

    def test_enums(self):
        self.assertEqual(RiskLevel.LOW.value, "LOW")
        self.assertEqual(RiskLevel.MODERATE.value, "MODERATE")
        self.assertEqual(RiskLevel.MEDIUM.value, "MEDIUM")
        self.assertEqual(RiskLevel.HIGH.value, "HIGH")
        self.assertEqual(RiskLevel.CRITICAL.value, "CRITICAL")
        self.assertEqual(RiskLevel.from_str("high"), RiskLevel.HIGH)

        self.assertEqual(RiskPriority.P1.value, "P1")
        self.assertEqual(RiskPriority.P2.value, "P2")
        self.assertEqual(RiskPriority.P3.value, "P3")
        self.assertEqual(RiskPriority.P4.value, "P4")
        self.assertEqual(RiskPriority.from_str("p1"), RiskPriority.P1)

        self.assertEqual(ConfidenceLevel.HIGH.value, "HIGH")
        self.assertEqual(ConfidenceLevel.MEDIUM.value, "MEDIUM")
        self.assertEqual(ConfidenceLevel.LOW.value, "LOW")
        self.assertEqual(ConfidenceLevel.from_str("medium"), ConfidenceLevel.MEDIUM)

    def test_risk_factor_creation_and_dict(self):
        factor = RiskFactor(
            factor_id="SEV_TAX_001",
            name="TAX_001 Severity (HIGH)",
            description="Tax rate mismatch",
            contribution=25.0,
            category="TAX",
            severity="HIGH",
            rule_id="TAX_001",
            evidence={"applied": 0.14, "expected": 0.18},
        )
        d = factor.to_dict()
        self.assertEqual(d["factor_id"], "SEV_TAX_001")
        self.assertEqual(d["contribution"], 25.0)
        self.assertEqual(d["category"], "TAX")
        self.assertEqual(d["evidence"]["applied"], 0.14)

    def test_risk_assessment_creation(self):
        assessment = RiskAssessment(
            invoice_id="INV-TEST-001",
            risk_score=75.0,
            risk_level=RiskLevel.HIGH,
            priority=RiskPriority.P2,
            confidence=ConfidenceLevel.HIGH,
            confidence_score=0.95,
            explanation="High risk due to tax rate discrepancy.",
            contributing_findings=["TAX_001"],
            category_scores={"TAX": 45.0},
            severity_contribution=25.0,
            data_quality_impact=0.0,
            risk_model_version="1.0",
        )
        self.assertEqual(assessment.risk_level, "HIGH")
        self.assertEqual(assessment.priority, "P2")
        self.assertEqual(assessment.confidence, "HIGH")
        self.assertIsNone(assessment.financial_exposure)
        self.assertIsNone(assessment.anomaly_score)

        d = assessment.to_dict()
        self.assertEqual(d["invoice_id"], "INV-TEST-001")
        self.assertEqual(d["risk_score"], 75.0)
        self.assertEqual(d["risk_model_version"], "1.0")

    def test_batch_risk_report(self):
        dist = RiskDistribution(
            total_invoices=10,
            by_level={"LOW": 5, "MODERATE": 2, "MEDIUM": 1, "HIGH": 1, "CRITICAL": 1},
            by_priority={"P1": 1, "P2": 1, "P3": 1, "P4": 7},
            by_category={"TAX": 2, "ITC": 1},
            average_risk_score=24.5,
        )
        report = BatchRiskReport(
            distribution=dist,
            top_risky_invoices=[],
            assessments=[],
        )
        self.assertEqual(report.distribution.total_invoices, 10)
        self.assertEqual(report.distribution.average_risk_score, 24.5)
        d = report.to_dict()
        self.assertIn("distribution", d)


if __name__ == "__main__":
    unittest.main()
