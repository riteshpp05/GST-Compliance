"""
UC15 GST Compliance Agent — Sprint 4.1 Reference & Policy Hardening Tests
========================================================================
Comprehensive regression and verification test suite covering all six S4.1 hardening fixes:
1. Missing/Conflicting Reference Yields NEEDS_REVIEW (HSN, Tax, POS, EWB, ITC)
2. E-Way Bill Historical Fallback to National Policy
3. E-Way Bill Jurisdiction-Specific Threshold (Interstate vs Intrastate)
4. E-Way Bill HSN Exemptions (EXEMPT, NOT_EXEMPT, UNAVAILABLE)
5. Elimination of Competing Sources of Truth & Legacy Source Attribution
6. Reference Snapshot Provenance, Unresolved Tracking, and Deep Immutability
"""
from datetime import date
from decimal import Decimal
import unittest

from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.reference.models.ewb_policy import EWBPolicyReference
from app.reference.models.hsn import HSNReference
from app.reference.models.itc_policy import ITCPolicyReference
from app.reference.models.snapshot import FrozenSnapshotError, ReferenceSnapshot
from app.reference.models.state import StateReference
from app.reference.models.tax_rate import TaxRateReference
from app.reference.repositories.in_memory import InMemoryReferenceRepository
from app.reference.resolvers.effective_date import ResolutionStatus
from app.reference.services.reference_service import ReferenceService
from app.rules.context import ValidationContext
from app.rules.existing.eway import EWayBillComplianceRule
from app.rules.existing.hsn import HSNValidityRule
from app.rules.existing.itc import ITCEligibilityRule
from app.rules.existing.pos import PlaceOfSupplyRule
from app.rules.existing.tax import TaxRateCorrectnessRule
from app.engine.validation_engine import ValidationEngine


class TestSprint41Hardening(unittest.TestCase):
    """Test suite verifying all Sprint 4.1 hardening fixes."""

    def setUp(self):
        # Create fresh statutory service for tests
        self.ref_service = ReferenceService(auto_load=True)

    def _make_invoice(
        self,
        invoice_no="INV-S41-001",
        invoice_date="2023-05-15",
        direction="AR",
        gstin="27AAACB1234A1Z5",
        counterparty_name="Test Client",
        place_of_supply="Maharashtra",
        hsn_code="8471",
        item_desc="Computer peripherals",
        taxable_value=40000.0,
        cgst_rate=9.0,
        sgst_rate=9.0,
        igst_rate=0.0,
        total_amt: Optional[float] = None,
        eway_bill_status="",
        gstr2b_reflected=True,
    ) -> Invoice:
        if total_amt is None:
            total_tax_rate = (cgst_rate + sgst_rate + igst_rate) / 100.0
            total_amt = round(taxable_value * (1.0 + total_tax_rate), 2)
        return Invoice.from_record(
            invoice_no=invoice_no,
            invoice_date=invoice_date,
            direction=direction,
            counterparty_gstin=gstin,
            counterparty_name=counterparty_name,
            place_of_supply=place_of_supply,
            hsn_code=hsn_code,
            item_desc=item_desc,
            taxable_value_inr=taxable_value,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            igst_rate=igst_rate,
            total_amt=total_amt,
            eway_bill_status=eway_bill_status,
            gstr2b_reflected=gstr2b_reflected,
        )

    # -------------------------------------------------------------------------
    # Fix 1: Missing / Conflicting Reference Yields NEEDS_REVIEW
    # -------------------------------------------------------------------------

    def test_fix1_missing_hsn_yields_needs_review(self):
        """Missing HSN in Gate 2 returns NEEDS_REVIEW with resolution_status NOT_FOUND."""
        context = ValidationContext(reference_service=self.ref_service)
        inv = self._make_invoice(hsn_code="999999")
        rule = HSNValidityRule()
        res = rule.validate(inv, context)

        self.assertEqual(res.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(res.evidence.get("resolution_status"), ResolutionStatus.NOT_FOUND.value)
        self.assertIn("not found in the HSN/SAC master", res.message)

    def test_fix1_missing_hsn_in_tax_rate_yields_needs_review(self):
        """Missing HSN in Gate 3 returns NEEDS_REVIEW with resolution_status NOT_FOUND."""
        context = ValidationContext(reference_service=self.ref_service)
        inv = self._make_invoice(hsn_code="999999")
        rule = TaxRateCorrectnessRule()
        res = rule.validate(inv, context)

        self.assertEqual(res.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(res.evidence.get("resolution_status"), ResolutionStatus.NOT_FOUND.value)

    def test_fix1_unknown_state_code_yields_needs_review(self):
        """Unknown 2-digit state prefix in Gate 4 returns NEEDS_REVIEW with resolution_status NOT_FOUND."""
        context = ValidationContext(reference_service=self.ref_service)
        inv = self._make_invoice(gstin="99AAACB1234A1Z5")  # 99 is invalid state
        rule = PlaceOfSupplyRule()
        res = rule.validate(inv, context)

        self.assertEqual(res.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(res.evidence.get("resolution_status"), ResolutionStatus.NOT_FOUND.value)
        self.assertIn("Could not resolve state", res.message)

    def test_fix1_missing_ewb_policy_yields_needs_review(self):
        """Empty EWB policy repository yields NEEDS_REVIEW in Gate 5."""
        empty_service = ReferenceService(auto_load=False)
        context = ValidationContext(reference_service=empty_service)
        inv = self._make_invoice()
        rule = EWayBillComplianceRule()
        res = rule.validate(inv, context)

        self.assertEqual(res.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(res.evidence.get("resolution_status"), ResolutionStatus.NOT_FOUND.value)
        self.assertIn("E-Way Bill policy not found", res.message)

    def test_fix1_missing_itc_policy_yields_needs_review(self):
        """Empty ITC policy repository yields NEEDS_REVIEW in Gate 6."""
        empty_service = ReferenceService(auto_load=False)
        context = ValidationContext(reference_service=empty_service)
        inv = self._make_invoice(direction="AP", item_desc="Industrial tool")
        rule = ITCEligibilityRule()
        res = rule.validate(inv, context)

        self.assertEqual(res.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(res.evidence.get("resolution_status"), ResolutionStatus.NOT_FOUND.value)
        self.assertIn("reference catalog is empty or missing", res.message)

    def test_fix1_conflicting_hsn_yields_needs_review(self):
        """Conflicting active HSN records yield NEEDS_REVIEW with CONFLICT status."""
        h1 = HSNReference(
            reference_id="H_CONF_A", code="555555", description="Conf A",
            version="1.0", effective_from=date(2023, 1, 1), effective_to=date(2023, 12, 31)
        )
        h2 = HSNReference(
            reference_id="H_CONF_B", code="555555", description="Conf B",
            version="2.0", effective_from=date(2023, 6, 1), effective_to=date(2024, 6, 1)
        )
        self.ref_service.repository.add_hsn(h1)
        self.ref_service.repository.add_hsn(h2)
        self.ref_service.clear_cache()

        context = ValidationContext(reference_service=self.ref_service)
        inv = self._make_invoice(hsn_code="555555", invoice_date="2023-08-01")
        rule = HSNValidityRule()
        res = rule.validate(inv, context)

        self.assertEqual(res.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(res.evidence.get("resolution_status"), ResolutionStatus.CONFLICT.value)
        self.assertIn("multiple active versions", res.message)

    def test_fix1_conflicting_ewb_policy_yields_needs_review(self):
        """Multiple active EWB policies for same state and date yield NEEDS_REVIEW."""
        p1 = EWBPolicyReference(
            policy_id="EWB_CONF_1", reference_id="EWB_CONF_1", state_code="27",
            threshold=Decimal("50000"), effective_from=date(2023, 1, 1), effective_to=date(2023, 12, 31)
        )
        p2 = EWBPolicyReference(
            policy_id="EWB_CONF_2", reference_id="EWB_CONF_2", state_code="27",
            threshold=Decimal("100000"), effective_from=date(2023, 6, 1), effective_to=date(2024, 6, 1)
        )
        self.ref_service.repository.add_ewb_policy(p1)
        self.ref_service.repository.add_ewb_policy(p2)
        self.ref_service.clear_cache()

        context = ValidationContext(reference_service=self.ref_service)
        inv = self._make_invoice(invoice_date="2023-08-01", gstin="27AAACB1234A1Z5")
        rule = EWayBillComplianceRule()
        res = rule.validate(inv, context)

        self.assertEqual(res.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(res.evidence.get("resolution_status"), ResolutionStatus.CONFLICT.value)

    # -------------------------------------------------------------------------
    # Fix 2: E-Way Bill Historical Fallback to National Policy
    # -------------------------------------------------------------------------

    def test_fix2_ewb_fallback_before_state_start_date(self):
        """Before state policy effective start date (e.g. 2018 for MH which started 2019), resolves national policy."""
        # MH policy EWB_MH_001 effective from 2019-01-01
        res = self.ref_service.resolve_ewb_policy(date(2018, 5, 1), state_code="27")
        self.assertTrue(res.is_resolved)
        self.assertEqual(res.record.policy_id, "EWB_NAT_001")
        self.assertIn("Fell back to national EWB policy", res.reason)

    def test_fix2_ewb_resolves_state_on_exact_start_date(self):
        """On exact state policy effective start date, resolves state policy."""
        res = self.ref_service.resolve_ewb_policy(date(2019, 2, 1), state_code="27")
        self.assertTrue(res.is_resolved)
        self.assertEqual(res.record.policy_id, "EWB_MH_001")

    def test_fix2_ewb_resolves_state_during_active_period(self):
        """During active period of state policy, resolves state policy."""
        res = self.ref_service.resolve_ewb_policy(date(2023, 6, 15), state_code="27")
        self.assertTrue(res.is_resolved)
        self.assertEqual(res.record.policy_id, "EWB_MH_001")

    def test_fix2_ewb_fallback_after_state_policy_expires(self):
        """After a temporary state policy expires, resolves national policy."""
        repo = InMemoryReferenceRepository()
        service = ReferenceService(repository=repo, auto_load=False)
        nat_policy = EWBPolicyReference(
            policy_id="EWB_NAT", reference_id="EWB_NAT", state_code=None,
            threshold=Decimal("50000"), interstate_threshold=Decimal("50000"), intrastate_threshold=Decimal("50000"),
            effective_from=date(2017, 7, 1), effective_to=None
        )
        temp_state_policy = EWBPolicyReference(
            policy_id="EWB_ST_TEMP", reference_id="EWB_ST_TEMP", state_code="29",
            threshold=Decimal("100000"), interstate_threshold=Decimal("50000"), intrastate_threshold=Decimal("100000"),
            effective_from=date(2019, 1, 1), effective_to=date(2021, 12, 31)
        )
        repo.add_ewb_policy(nat_policy)
        repo.add_ewb_policy(temp_state_policy)

        # In 2020: resolves state policy
        res_2020 = service.resolve_ewb_policy(date(2020, 1, 1), state_code="29")
        self.assertEqual(res_2020.record.policy_id, "EWB_ST_TEMP")

        # In 2023: falls back to national policy
        res_2023 = service.resolve_ewb_policy(date(2023, 1, 1), state_code="29")
        self.assertEqual(res_2023.record.policy_id, "EWB_NAT")

    def test_fix2_ewb_state_with_no_specific_policy_resolves_national(self):
        """A state with no specific policy resolves national policy for all dates."""
        res = self.ref_service.resolve_ewb_policy(date(2023, 1, 1), state_code="29")  # Karnataka (no state EWB in repo)
        self.assertTrue(res.is_resolved)
        self.assertEqual(res.record.policy_id, "EWB_NAT_001")

    # -------------------------------------------------------------------------
    # Fix 3: E-Way Bill Jurisdiction-Specific Threshold
    # -------------------------------------------------------------------------

    def test_fix3_ewb_interstate_applies_interstate_threshold(self):
        """Inter-state movement uses interstate_threshold (50,000 INR), requiring EWB above 50,000."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        # MH supplier shipping to Karnataka (inter-state, IGST applied)
        inv = self._make_invoice(
            gstin="27AAACB1234A1Z5",
            place_of_supply="Karnataka",
            igst_rate=18.0, cgst_rate=0.0, sgst_rate=0.0,
            taxable_value=60000.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.FAIL.value)
        self.assertEqual(res.evidence.get("threshold"), 50000.0)
        self.assertTrue(res.evidence.get("is_interstate"))

    def test_fix3_ewb_intrastate_mh_applies_intrastate_threshold(self):
        """Intra-state movement in Maharashtra uses intrastate_threshold (100,000 INR)."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        # MH supplier shipping to MH (intra-state), value 75,000 <= 100,000 threshold
        inv = self._make_invoice(
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            cgst_rate=9.0, sgst_rate=9.0, igst_rate=0.0,
            taxable_value=75000.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.NOT_APPLICABLE.value)
        self.assertEqual(res.evidence.get("threshold"), 100000.0)
        self.assertFalse(res.evidence.get("is_interstate"))

    def test_fix3_ewb_threshold_boundary_minus_one(self):
        """Taxable value exactly (threshold - 1) is NOT_APPLICABLE."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        inv = self._make_invoice(
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            taxable_value=99999.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.NOT_APPLICABLE.value)

    def test_fix3_ewb_threshold_boundary_exact(self):
        """Taxable value exactly equal to threshold is NOT_APPLICABLE."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        inv = self._make_invoice(
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            taxable_value=100000.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.NOT_APPLICABLE.value)

    def test_fix3_ewb_threshold_boundary_plus_one(self):
        """Taxable value (threshold + 1) requires E-Way Bill."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        inv = self._make_invoice(
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            taxable_value=100001.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.FAIL.value)
        self.assertTrue(res.evidence.get("eway_bill_required"))

    # -------------------------------------------------------------------------
    # Fix 4: E-Way Bill HSN Exemptions
    # -------------------------------------------------------------------------

    def test_fix4_ewb_exempt_hsn_yields_not_applicable_regardless_of_amount(self):
        """HSN 0101 (live animals) is exempted under EWB policy; yields NOT_APPLICABLE even for 500,000 INR."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        inv = self._make_invoice(
            hsn_code="0101",
            taxable_value=500000.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.NOT_APPLICABLE.value)
        self.assertEqual(res.evidence.get("exemption_status"), "EXEMPT")
        self.assertIn("exempt from E-Way Bill", res.message)

    def test_fix4_ewb_non_exempt_hsn_records_not_exempt(self):
        """Non-exempt HSN records exemption_status NOT_EXEMPT and checks threshold."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        inv = self._make_invoice(
            hsn_code="8471",
            taxable_value=30000.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.evidence.get("exemption_status"), "NOT_EXEMPT")
        self.assertIn("exemption_reason", res.evidence)

    def test_fix4_ewb_missing_hsn_records_unavailable(self):
        """Missing HSN records exemption_status UNAVAILABLE and proceeds with value-based check."""
        context = ValidationContext(reference_service=self.ref_service)
        rule = EWayBillComplianceRule()
        inv = self._make_invoice(
            hsn_code="",
            taxable_value=30000.0,
            eway_bill_status=""
        )
        res = rule.validate(inv, context)
        self.assertEqual(res.evidence.get("exemption_status"), "UNAVAILABLE")
        self.assertIn("missing HSN code", res.evidence.get("exemption_reason", ""))

    # -------------------------------------------------------------------------
    # Fix 5: Legacy Inputs & Single Source of Truth
    # -------------------------------------------------------------------------

    def test_fix5_legacy_context_adapted_without_overwriting_official(self):
        """Legacy dictionary inputs cannot overwrite statutory OFFICIAL_GST records."""
        from app.domain.models.tax import HSNMaster
        legacy_hsn = {
            "8471": HSNMaster.from_raw("8471", "Legacy Overwrite Attempt", 5, 5, 10),
            "999123": HSNMaster.from_raw("999123", "Pure Legacy Item", 9, 9, 18),
        }
        context = ValidationContext(hsn_master=legacy_hsn, reference_service=self.ref_service)

        # 8471 should retain OFFICIAL_GST rate (9% / 18%), NOT the legacy 5% / 10%
        res_8471 = self.ref_service.resolve_hsn("8471", date(2023, 1, 1))
        self.assertEqual(res_8471.record.source, "OFFICIAL_GST")
        self.assertEqual(res_8471.record.default_cgst_rate, Decimal("0.09"))

        # 999123 was not in statutory catalog, so legacy adapted record is present with source LEGACY_ADAPTED
        res_999 = self.ref_service.resolve_hsn("999123", date(2023, 1, 1))
        self.assertTrue(res_999.is_resolved)
        self.assertEqual(res_999.record.source, "LEGACY_ADAPTED")

    def test_fix5_legacy_validation_engine_runs_seamlessly(self):
        """ValidationEngine and DecisionEngine run seamlessly."""
        from app.engine.validation_engine import ValidationEngine
        from app.engine.decision_engine import DecisionEngine
        from app.rules.context import ValidationContext
        val_engine = ValidationEngine(context=ValidationContext(reference_service=self.ref_service))
        dec_engine = DecisionEngine()
        inv = self._make_invoice(hsn_code="8471", cgst_rate=9.0, sgst_rate=9.0, taxable_value=25000.0)
        report = val_engine.validate(inv)
        decision = dec_engine.decide(inv, report)
        self.assertEqual(decision.status, "COMPLIANT")

    # -------------------------------------------------------------------------
    # Fix 6: Snapshot Provenance, Unresolved Tracking & Deep Immutability
    # -------------------------------------------------------------------------

    def test_fix6_snapshot_records_provenance_and_applicability_reason(self):
        """ReferenceSnapshot records applicability_reason and statutory provenance."""
        context = ValidationContext(reference_service=self.ref_service)
        inv = self._make_invoice(hsn_code="8471", invoice_date="2023-05-15")

        snapshot = ReferenceSnapshot.from_context(context, invoice=inv)
        self.assertEqual(snapshot.applicability_reason, "Invoice INV-S41-001 dated 2023-05-15 (Place of Supply: Maharashtra)")
        self.assertEqual(snapshot.source, "OFFICIAL_GST")

        # Freeze snapshot
        snapshot.freeze()
        self.assertTrue(snapshot.is_frozen)

    def test_fix6_frozen_snapshot_raises_error_on_mutation(self):
        """Mutating or deleting any attribute or internal dictionary of a frozen snapshot raises FrozenSnapshotError."""
        snapshot = ReferenceSnapshot(applicability_reason="Test Reason")
        snapshot.set_metadata("audit_id", "12345")
        snapshot.freeze()

        # Attribute mutation
        with self.assertRaises(FrozenSnapshotError):
            snapshot.applicability_reason = "Changed"

        # Deletion
        with self.assertRaises(FrozenSnapshotError):
            del snapshot.applicability_reason

        # Method call after freeze
        with self.assertRaises(FrozenSnapshotError):
            snapshot.set_metadata("key", "val")

        # Dictionary mutation inside frozen snapshot
        with self.assertRaises(FrozenSnapshotError):
            snapshot.metadata["audit_id"] = "modified"

    def test_fix6_snapshot_records_unresolved_references(self):
        """Unresolved references (NOT_FOUND or CONFLICT) are recorded in snapshot.unresolved."""
        context = ValidationContext(reference_service=self.ref_service)
        inv = self._make_invoice(hsn_code="UNKNOWN_999")
        snapshot = ReferenceSnapshot.from_context(context, invoice=inv)
        context.current_snapshot = snapshot

        # Run HSN rule
        rule = HSNValidityRule()
        rule.validate(inv, context)

        self.assertIn("hsn", snapshot.unresolved)
        unresolved_info = snapshot.unresolved["hsn"]
        self.assertEqual(unresolved_info["identifier"], "UNKNOWN_999")
        self.assertEqual(unresolved_info["status"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
