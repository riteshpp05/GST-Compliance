"""
UC15 GST Compliance Agent — Unit Tests: Reference Service (Sprint 4)
Tests the centralized enterprise ReferenceService for statutory resolution, caching, and snapshots.
"""
import unittest
from datetime import date
from decimal import Decimal

from app.reference.resolvers.effective_date import ResolutionStatus
from app.reference.services.reference_service import ReferenceService


class TestReferenceService(unittest.TestCase):
    """Unit tests for ReferenceService resolution logic and catalog querying."""

    @classmethod
    def setUpClass(cls):
        cls.service = ReferenceService()

    def test_hsn_resolution_exact_and_prefix(self):
        """Test exact HSN match and hierarchical prefix fallback."""
        d = date(2023, 6, 1)
        # Exact match
        res_exact = self.service.resolve_hsn("84713010", d)
        self.assertTrue(res_exact.is_resolved)
        self.assertEqual(res_exact.record.code, "84713010")

        # Fallback to 4-digit heading 8471 when 8-digit tariff item not explicitly listed
        res_prefix = self.service.resolve_hsn("84719000", d)
        self.assertTrue(res_prefix.is_resolved)
        self.assertEqual(res_prefix.record.code, "8471")

    def test_tax_rate_resolution_temporal_shift(self):
        """Test rate resolution across historical date boundary."""
        hsn = "84713010_TEMP"
        # Before 2022-01-01: 12% IGST (6% CGST + 6% SGST)
        res_old = self.service.resolve_tax_rate(hsn, date(2020, 5, 10))
        self.assertTrue(res_old.is_resolved)
        self.assertEqual(res_old.record.cgst_rate, Decimal("0.06"))
        self.assertEqual(res_old.record.version, "1.0")

        # From 2022-01-01 onwards: 18% IGST (9% CGST + 9% SGST)
        res_new = self.service.resolve_tax_rate(hsn, date(2022, 3, 15))
        self.assertTrue(res_new.is_resolved)
        self.assertEqual(res_new.record.cgst_rate, Decimal("0.09"))
        self.assertEqual(res_new.record.version, "2.0")

    def test_state_resolution_and_padding(self):
        """Test state code lookup with single digit normalization."""
        # Unpadded '7' -> '07' (Delhi)
        res_delhi = self.service.resolve_state("7", date(2023, 1, 1))
        self.assertTrue(res_delhi.is_resolved)
        self.assertEqual(res_delhi.record.state_name, "Delhi")
        self.assertEqual(res_delhi.record.state_or_ut, "UT")

        # Padded '27' (Maharashtra)
        res_mh = self.service.resolve_state("27", date(2023, 1, 1))
        self.assertTrue(res_mh.is_resolved)
        self.assertEqual(res_mh.record.state_name, "Maharashtra")

    def test_ewb_policy_national_vs_jurisdiction(self):
        """Test national default EWB threshold vs state-specific elevated threshold."""
        d = date(2023, 1, 1)
        # National movement policy
        res_nat = self.service.resolve_ewb_policy(d)
        self.assertTrue(res_nat.is_resolved)
        self.assertEqual(res_nat.record.threshold, Decimal("50000.00"))

        # Maharashtra movement policy (intrastate 100,000)
        res_mh = self.service.resolve_ewb_policy(d, state_code="27")
        self.assertTrue(res_mh.is_resolved)
        self.assertEqual(res_mh.record.intrastate_threshold, Decimal("100000.00"))

    def test_itc_policy_resolution(self):
        """Test ITC Section 17(5) restriction policy matching."""
        d = date(2023, 1, 1)
        # Blocked motor vehicles
        res_car = self.service.resolve_itc_policy("Luxury motor vehicle for directors", d)
        self.assertTrue(res_car.is_resolved)
        self.assertEqual(res_car.record.category, "MOTOR_VEHICLES")
        self.assertTrue(res_car.record.is_blocked_17_5)

        # Blocked food & catering
        res_food = self.service.resolve_itc_policy("Executive lunch catering expenses", d)
        self.assertTrue(res_food.is_resolved)
        self.assertTrue(res_food.record.is_blocked_17_5)

        # Unblocked general hardware
        res_hw = self.service.resolve_itc_policy("Server rack switches and cables", d)
        self.assertEqual(res_hw.status, ResolutionStatus.NOT_FOUND)

    def test_caching_and_snapshot_creation(self):
        """Test resolution cache reuse and snapshot generation."""
        d = date(2023, 1, 1)
        res1 = self.service.resolve_hsn("8471", d)
        res2 = self.service.resolve_hsn("8471", d)
        self.assertIs(res1, res2)  # Cache hit returns identical instance

        snap = self.service.create_snapshot("INV-999", d)
        self.assertEqual(snap.invoice_id, "INV-999")
        self.assertEqual(snap.transaction_date, "2023-01-01")


if __name__ == "__main__":
    unittest.main()
