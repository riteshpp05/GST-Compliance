"""
UC15 GST Compliance Agent — Duplicate Intelligence Unit Test Suite (Sprint 7)
Verifies:
  1. Exact Duplicate Detection (identical invoice number, supplier GSTIN, taxable value, invoice date)
  2. Near Duplicate Detection (similar invoice numbers with prefix/suffix/case variation, same supplier, same date/value)
  3. Date Shift Duplicate Detection (same supplier, invoice number, amount, small date variance <= 3 days)
  4. Amount Variance Duplicate Detection (same supplier, invoice number, date, slight amount rounding <= 1.00)
  5. False Positive Protection (different suppliers, different amounts, recurring monthly invoices with standard intervals)
  6. Duplicate Clustering (transitive duplicates form correct clusters with stable anchor)
  7. Missing Field Handling (graceful handling of missing optional fields without crashes or false duplicates)
  8. Confidence Scoring & Structured Evidence
"""
import unittest
from datetime import date
from decimal import Decimal
from typing import List

from app.domain.models.invoice import Invoice
from app.intelligence.common.enums import DuplicateMatchType, IntelligenceConfidence
from app.intelligence.config.intelligence_config import DuplicatePolicyConfig
from app.intelligence.duplicate.clusterer import DuplicateClusterer
from app.intelligence.duplicate.engine import DuplicateIntelligenceEngine
from app.intelligence.duplicate.exact_detector import ExactDuplicateDetector
from app.intelligence.duplicate.fingerprint import (
    compute_string_similarity,
    extract_parties,
    generate_exact_fingerprint,
    levenshtein_distance,
    normalize_invoice_number,
)
from app.intelligence.duplicate.near_detector import NearDuplicateDetector
from tests.fixtures.sample_invoices import make_test_invoice


class TestDuplicateFingerprint(unittest.TestCase):
    """Test fingerprinting and normalization utilities."""

    def test_normalize_invoice_number(self):
        self.assertEqual(normalize_invoice_number("INV-2026/001"), "INV2026001")
        self.assertEqual(normalize_invoice_number("  inv # 001-A  "), "INV001A")
        self.assertEqual(normalize_invoice_number(None), "")

    def test_levenshtein_and_similarity(self):
        self.assertEqual(levenshtein_distance("INV001", "INV001"), 0)
        self.assertEqual(levenshtein_distance("INV001", "INV002"), 1)
        self.assertAlmostEqual(compute_string_similarity("INV001", "INV001"), 1.0)
        self.assertGreater(compute_string_similarity("INV-001", "INV001"), 0.8)

    def test_party_gstin_extraction(self):
        inv_ap = make_test_invoice(invoice_no="INV-1", direction="AP", gstin="27AAACB1234A1Z5")
        supplier, _ = extract_parties(inv_ap)
        self.assertEqual(supplier, "27AAACB1234A1Z5")

        inv_ar = make_test_invoice(invoice_no="INV-2", direction="AR", gstin="27AAACB1234A1Z5")
        _, buyer = extract_parties(inv_ar)
        self.assertEqual(buyer, "27AAACB1234A1Z5")


class TestExactDuplicateDetector(unittest.TestCase):
    """Test exact duplicate detection."""

    def setUp(self):
        self.config = DuplicatePolicyConfig()
        self.detector = ExactDuplicateDetector(self.config)

    def test_exact_duplicate_detected(self):
        inv1 = make_test_invoice(
            invoice_id="REC-001",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )
        inv2 = make_test_invoice(
            invoice_id="REC-002",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )

        candidates = self.detector.detect_exact([inv1, inv2])
        exacts = [c for c in candidates if c.match_type == DuplicateMatchType.EXACT_DUPLICATE]
        self.assertEqual(len(exacts), 1)
        cand = exacts[0]
        self.assertEqual(cand.match_type, DuplicateMatchType.EXACT_DUPLICATE)
        self.assertEqual(cand.similarity_score, 100.0)
        self.assertEqual(cand.confidence, IntelligenceConfidence.HIGH)
        self.assertTrue(cand.evidence.get("is_exact"))

    def test_distinct_invoices_no_duplicate(self):
        inv1 = make_test_invoice(invoice_id="REC-001", invoice_no="INV-001", gstin="27AAACB1234A1Z5")
        inv2 = make_test_invoice(invoice_id="REC-002", invoice_no="INV-002", gstin="27AAACB1234A1Z5")
        candidates = self.detector.detect_exact([inv1, inv2])
        exacts = [c for c in candidates if c.match_type == DuplicateMatchType.EXACT_DUPLICATE]
        self.assertEqual(len(exacts), 0)


class TestNearDuplicateDetector(unittest.TestCase):
    """Test near duplicate, date-shift, amount-variance, and false-positive protection."""

    def setUp(self):
        self.config = DuplicatePolicyConfig()
        self.detector = NearDuplicateDetector(self.config)

    def test_near_duplicate_similar_invoice_number(self):
        # e.g., INV-2026-001 vs INV-2026-001A with same supplier, date, amount
        inv1 = make_test_invoice(
            invoice_id="REC-001",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )
        inv2 = make_test_invoice(
            invoice_id="REC-002",
            invoice_no="INV-2026-001A",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )
        cand = self.detector.compare_pair(inv1, inv2)
        self.assertIn(cand.match_type, [DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE, DuplicateMatchType.POSSIBLE_DUPLICATE])
        self.assertGreaterEqual(cand.similarity_score, 65.0)

    def test_date_shift_duplicate(self):
        # Same supplier, same invoice number, same amount, date shifted by 2 days (<= 3 days)
        inv1 = make_test_invoice(
            invoice_id="REC-001",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )
        inv2 = make_test_invoice(
            invoice_id="REC-002",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-03",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )
        cand = self.detector.compare_pair(inv1, inv2)
        self.assertIn(cand.match_type, [DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE, DuplicateMatchType.POSSIBLE_DUPLICATE])
        self.assertGreaterEqual(cand.similarity_score, 80.0)

    def test_amount_variance_duplicate(self):
        # Same supplier, same invoice number, same date, amount differing by 0.50 (<= 1.00)
        inv1 = make_test_invoice(
            invoice_id="REC-001",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.00,
        )
        inv2 = make_test_invoice(
            invoice_id="REC-002",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.50,
            total_amt=59000.50,
        )
        cand = self.detector.compare_pair(inv1, inv2)
        self.assertIn(cand.match_type, [DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE, DuplicateMatchType.POSSIBLE_DUPLICATE])
        self.assertGreaterEqual(cand.similarity_score, 90.0)

    def test_false_positive_different_suppliers(self):
        # Same invoice number and amount, but DIFFERENT suppliers -> NOT duplicate
        inv1 = make_test_invoice(
            invoice_id="REC-001",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
        )
        inv2 = make_test_invoice(
            invoice_id="REC-002",
            invoice_no="INV-2026-001",
            invoice_date="2026-03-01",
            direction="AP",
            gstin="29BBBCB5678B2Z6",
            taxable_value=50000.0,
        )
        cand = self.detector.compare_pair(inv1, inv2)
        self.assertEqual(cand.match_type, DuplicateMatchType.NO_DUPLICATE)

    def test_false_positive_recurring_monthly_invoices(self):
        # Same supplier and same amount, but dates 31 days apart and different invoice numbers (e.g. monthly retainer)
        inv1 = make_test_invoice(
            invoice_id="REC-001",
            invoice_no="RENT-JAN-2026",
            invoice_date="2026-01-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )
        inv2 = make_test_invoice(
            invoice_id="REC-002",
            invoice_no="RENT-FEB-2026",
            invoice_date="2026-02-01",
            direction="AP",
            gstin="27AAACB1234A1Z5",
            taxable_value=50000.0,
            total_amt=59000.0,
        )
        cand = self.detector.compare_pair(inv1, inv2)
        self.assertEqual(cand.match_type, DuplicateMatchType.NO_DUPLICATE)
        self.assertTrue(cand.is_recurring_legitimate)


class TestDuplicateClustering(unittest.TestCase):
    """Test multi-invoice duplicate clustering with graph connected components."""

    def test_transitive_clustering(self):
        invA = make_test_invoice(invoice_id="REC-A", invoice_no="INV-001", invoice_date="2026-03-01", gstin="27AAACB1234A1Z5", taxable_value=10000.0)
        invB = make_test_invoice(invoice_id="REC-B", invoice_no="INV-001", invoice_date="2026-03-01", gstin="27AAACB1234A1Z5", taxable_value=10000.0)
        invC = make_test_invoice(invoice_id="REC-C", invoice_no="INV-001", invoice_date="2026-03-01", gstin="27AAACB1234A1Z5", taxable_value=10000.0)

        engine = DuplicateIntelligenceEngine()
        clusters, candidates, findings = engine.analyze([invA, invB, invC])
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(len(clusters), 1)
        cluster = clusters[0]
        self.assertEqual(cluster.invoice_count, 3)
        self.assertEqual(cluster.anchor_invoice_id, "REC-A")


class TestDuplicateEngineEdgeCases(unittest.TestCase):
    """Test edge cases: empty list, single invoice, missing optional fields."""

    def setUp(self):
        self.engine = DuplicateIntelligenceEngine()

    def test_empty_and_single_invoice(self):
        clusters, candidates, findings = self.engine.analyze([])
        self.assertEqual(len(candidates), 0)
        self.assertEqual(len(clusters), 0)

        inv = make_test_invoice(invoice_id="REC-001")
        clusters_single, candidates_single, findings_single = self.engine.analyze([inv])
        self.assertEqual(len(candidates_single), 0)
        self.assertEqual(len(clusters_single), 0)

    def test_missing_optional_fields_graceful(self):
        inv1 = make_test_invoice(
            invoice_id="REC-001",
            invoice_no="INV-ALPHA-101",
            invoice_date="2026-01-10",
            taxable_value=12000.0,
            place_of_supply="",
            item_desc="",
            eway_bill="",
        )
        inv2 = make_test_invoice(
            invoice_id="REC-002",
            invoice_no="INV-BETA-909",
            invoice_date="2026-04-15",
            taxable_value=85000.0,
            place_of_supply="",
            item_desc="",
            eway_bill="",
        )
        clusters, candidates, findings = self.engine.analyze([inv1, inv2])
        self.assertEqual(len(clusters), 0)


if __name__ == "__main__":
    unittest.main()
