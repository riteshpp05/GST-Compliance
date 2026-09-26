"""
UC15 GST Compliance Agent — Unit Tests: Reference Domain Models (Sprint 4)
Tests structural integrity, validation rules, hierarchy, and snapshots for reference data contracts.
"""
import unittest
from datetime import date
from decimal import Decimal

from app.reference.models.base import BaseReferenceRecord
from app.reference.models.ewb_policy import EWBPolicyReference
from app.reference.models.hsn import HSNReference
from app.reference.models.itc_policy import ITCPolicyReference
from app.reference.models.snapshot import ReferenceSnapshot
from app.reference.models.state import StateReference
from app.reference.models.tax_rate import TaxRateReference


class TestReferenceModels(unittest.TestCase):
    """Unit tests for statutory reference entity models."""

    def test_base_reference_integrity_and_dates(self):
        """Test base reference validation and temporal date checking."""
        rec = BaseReferenceRecord(
            reference_id="TEST_REF_01",
            reference_type="TEST",
            version="1.0",
            effective_from=date(2020, 1, 1),
            effective_to=date(2022, 12, 31),
            status="ACTIVE",
        )
        self.assertEqual(rec.validate_integrity(), [])
        self.assertFalse(rec.is_active_on(date(2019, 12, 31)))
        self.assertTrue(rec.is_active_on(date(2020, 1, 1)))
        self.assertTrue(rec.is_active_on(date(2021, 6, 15)))
        self.assertTrue(rec.is_active_on(date(2022, 12, 31)))
        self.assertFalse(rec.is_active_on(date(2023, 1, 1)))

    def test_base_reference_inverted_dates(self):
        """Test detection of inverted date ranges."""
        rec = BaseReferenceRecord(
            reference_id="TEST_INVALID",
            reference_type="TEST",
            version="1.0",
            effective_from=date(2023, 1, 1),
            effective_to=date(2020, 1, 1),
        )
        issues = rec.validate_integrity()
        self.assertTrue(any("effective_from must be on or before effective_to" in i for i in issues))

    def test_hsn_model_hierarchy_and_services(self):
        """Test HSN code classification, service distinction, and rate integrity."""
        # 8-digit tariff item
        hsn_goods = HSNReference(
            reference_id="HSN_84713010",
            code="84713010",
            description="Laptops",
            default_cgst_rate=Decimal("0.09"),
            default_sgst_rate=Decimal("0.09"),
            default_igst_rate=Decimal("0.18"),
        )
        self.assertFalse(hsn_goods.is_service)
        self.assertEqual(hsn_goods.chapter, "84")
        self.assertEqual(hsn_goods.heading, "8471")
        self.assertEqual(hsn_goods.subheading, "847130")
        self.assertEqual(hsn_goods.tariff_item, "84713010")
        self.assertEqual(hsn_goods.validate_integrity(), [])

        # 6-digit SAC service code
        sac_service = HSNReference(
            reference_id="SAC_998313",
            code="998313",
            description="IT Consulting",
            code_type="SAC",
        )
        self.assertTrue(sac_service.is_service)
        self.assertEqual(sac_service.heading, "9983")

    def test_tax_rate_model_rates_and_computations(self):
        """Test tax rate Decimal conversion, total intra rate calculation, and integrity."""
        rate = TaxRateReference(
            reference_id="TAX_TEST_01",
            hsn_code="8471",
            cgst_rate="0.09",
            sgst_rate="0.09",
            igst_rate="0.18",
            cess_rate="0.00",
        )
        self.assertEqual(rate.total_intra_rate, Decimal("0.18"))
        self.assertEqual(rate.validate_integrity(), [])

        # Negative rate integrity failure
        invalid_rate = TaxRateReference(
            reference_id="TAX_NEG",
            hsn_code="8471",
            cgst_rate="-0.05",
        )
        self.assertTrue(any("cgst_rate cannot be negative" in i for i in invalid_rate.validate_integrity()))

    def test_state_model_padding_and_classification(self):
        """Test state 2-digit padding and UT vs State categorization."""
        st = StateReference(
            reference_id="STATE_07",
            state_code="7",  # Unpadded
            state_name="Delhi",
            state_or_ut="UT",
        )
        self.assertEqual(st.state_code, "07")
        self.assertEqual(st.state_or_ut, "UT")
        self.assertEqual(st.validate_integrity(), [])

    def test_ewb_policy_jurisdiction_thresholds(self):
        """Test E-Way Bill threshold lookups for inter vs intra state movements."""
        pol = EWBPolicyReference(
            reference_id="EWB_MH_TEST",
            threshold=Decimal("50000.00"),
            interstate_threshold=Decimal("50000.00"),
            intrastate_threshold=Decimal("100000.00"),
        )
        self.assertEqual(pol.get_threshold_for(is_interstate=True), Decimal("50000.00"))
        self.assertEqual(pol.get_threshold_for(is_interstate=False), Decimal("100000.00"))

    def test_itc_policy_keyword_matching(self):
        """Test ITC Section 17(5) blocked keyword matching logic."""
        pol = ITCPolicyReference(
            reference_id="ITC_MOTOR_TEST",
            category="MOTOR_VEHICLES",
            blocked_keywords=["motor car", "vehicle", "passenger cab"],
            is_blocked_17_5=True,
        )
        self.assertTrue(pol.matches_item_description("Purchase of motor car for office use"))
        self.assertTrue(pol.matches_item_description("Company Passenger Cab lease"))
        self.assertFalse(pol.matches_item_description("Office laptops and stationery"))

    def test_reference_snapshot_recording(self):
        """Test ReferenceSnapshot immutable audit trail generation."""
        snap = ReferenceSnapshot(
            invoice_id="INV-TEST-001",
            transaction_date="2023-08-15",
        )
        hsn = HSNReference(reference_id="HSN_REF_01", version="2.1", code="8471", description="Computers")
        snap.set_hsn(hsn)
        st = StateReference(reference_id="STATE_27", version="1.0", state_code="27", state_name="Maharashtra")
        snap.set_state(st)

        self.assertEqual(snap.hsn_reference_id, "HSN_REF_01")
        self.assertEqual(snap.hsn_reference_version, "2.1")
        self.assertEqual(snap.state_reference_id, "STATE_27")
        self.assertEqual(snap.state_reference_version, "1.0")

        d = snap.to_dict()
        self.assertEqual(d["invoice_id"], "INV-TEST-001")
        self.assertIn("HSN", d["resolved_records"])
        self.assertIn("STATE", d["resolved_records"])


if __name__ == "__main__":
    unittest.main()
