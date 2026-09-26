"""
tests.unit.test_s17_quality
============================
Sprint 17 Unit Test Suite: Data Quality Engine & Provenance Lineage.
"""

import unittest
from app.data.lineage import LineageTracker
from app.data.quality import DataQualityEngine, QualityStatus
from app.domain.models.invoice import Invoice


class TestS17DataQualityEngine(unittest.TestCase):
    """Test suite for 6-dimension data quality scoring and record evaluations."""

    def test_record_quality_scoring_dimensions(self):
        inv = Invoice(
            invoice_id="INV-500",
            invoice_number="INV-500",
            invoice_date="2026-04-01",
            counterparty_name="Acme Corp",
            gstin="27ABCDE1234F1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="3926",
            taxable_value=10000.0,
            total_tax=1800.0,
            total_amount=11800.0,
        )

        res = DataQualityEngine.evaluate_record(
            record_id="REC-001",
            record_index=1,
            raw_record={},
            canonical_invoice=inv,
            duplicate_status="UNIQUE",
        )

        self.assertGreaterEqual(res.quality_score, 80.0)
        self.assertEqual(res.status, "ACCEPTED")
        self.assertIn("COMPLETENESS", res.dimension_scores)
        self.assertIn("VALIDITY", res.dimension_scores)
        self.assertIn("CONSISTENCY", res.dimension_scores)
        self.assertIn("UNIQUENESS", res.dimension_scores)
        self.assertIn("ACCURACY", res.dimension_scores)
        self.assertIn("TIMELINESS", res.dimension_scores)

    def test_batch_quality_report_aggregation(self):
        inv = Invoice(
            invoice_id="INV-501",
            invoice_number="INV-501",
            invoice_date="2026-04-01",
            counterparty_name="Acme Corp",
            gstin="27ABCDE1234F1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="3926",
            taxable_value=10000.0,
            total_tax=1800.0,
            total_amount=11800.0,
        )

        r1 = DataQualityEngine.evaluate_record("REC-001", 1, {}, inv, "UNIQUE")
        r2 = DataQualityEngine.evaluate_record("REC-002", 2, {}, None, "UNIQUE", structural_errors=["Missing required field"])

        report = DataQualityEngine.evaluate_batch(ingestion_id="INGEST-TEST-01", records=[r1, r2])

        self.assertEqual(report.total_records, 2)
        self.assertEqual(report.accepted_records, 1)
        self.assertEqual(report.rejected_records, 1)
        self.assertIn("overall_quality_score", report.to_dict())

    def test_data_lineage_creation_and_linking(self):
        lin = LineageTracker.create_lineage(
            ingestion_id="INGEST-100",
            source_id="SRC-CSV",
            source_record_id="ROW-1",
            canonical_record_id="INV-600",
        )

        self.assertEqual(lin.ingestion_id, "INGEST-100")
        self.assertEqual(lin.canonical_record_id, "INV-600")

        updated = LineageTracker.link_downstream_case(lin, case_id="CASE-8888", evidence_ids=["EVD-01"])
        self.assertEqual(updated.downstream_case_id, "CASE-8888")
        self.assertIn("EVD-01", updated.downstream_evidence_ids)
