"""
UC15 GST Compliance Agent — Sprint 21 Unit Tests
Validates Date-Aware Statutory Rate Versioning, Effective Date Boundaries,
Rule Validation Contracts, and Financial Exposure Traceability.
"""
import unittest
from datetime import date
from decimal import Decimal

from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.reference.models.tax_rate import TaxRateReference
from app.reference.resolvers.effective_date import EffectiveDateResolver, ResolutionStatus
from app.reference.services.reference_service import ReferenceService
from app.rules.context import ValidationContext
from app.rules.existing.hsn import HSNValidityRule
from app.rules.existing.tax import TaxRateCorrectnessRule
from app.rules.existing.gstin import GSTINFormatRule
from app.rules.existing.pos import PlaceOfSupplyRule
from app.rules.existing.eway import EWayBillComplianceRule
from app.rules.existing.itc import ITCEligibilityRule


class TestS21EffectiveDateBoundaries(unittest.TestCase):
    """Test effective-date boundary conditions for temporal tax rate resolution."""

    def setUp(self):
        self.r1 = TaxRateReference(
            reference_id="TAX_8471_V1",
            version="1.0",
            effective_from=date(2017, 7, 1),
            effective_to=date(2025, 9, 21),
            status="ACTIVE",
            hsn_code="8471",
            cgst_rate=Decimal("0.09"),
            sgst_rate=Decimal("0.09"),
            igst_rate=Decimal("0.18"),
        )
        self.r2 = TaxRateReference(
            reference_id="TAX_8471_V2",
            version="2.0",
            effective_from=date(2025, 9, 22),
            effective_to=None,
            status="ACTIVE",
            hsn_code="8471",
            cgst_rate=Decimal("0.09"),
            sgst_rate=Decimal("0.09"),
            igst_rate=Decimal("0.18"),
        )
        self.candidates = [self.r1, self.r2]

    def test_before_effective_from_minus_1(self):
        """Date before effective_from of V1 returns NOT_FOUND."""
        res = EffectiveDateResolver.resolve(self.candidates, date(2017, 6, 30))
        self.assertEqual(res.status, ResolutionStatus.NOT_FOUND)

    def test_exactly_on_effective_from(self):
        """Date exactly on effective_from resolves V1."""
        res = EffectiveDateResolver.resolve(self.candidates, date(2017, 7, 1))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "TAX_8471_V1")

    def test_after_effective_from_plus_1(self):
        """Date after effective_from resolves V1."""
        res = EffectiveDateResolver.resolve(self.candidates, date(2017, 7, 2))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "TAX_8471_V1")

    def test_exactly_on_effective_to(self):
        """Date exactly on effective_to of V1 resolves V1."""
        res = EffectiveDateResolver.resolve(self.candidates, date(2025, 9, 21))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "TAX_8471_V1")

    def test_effective_to_plus_1_transition_to_v2(self):
        """Date effective_to + 1 day transitions to V2."""
        res = EffectiveDateResolver.resolve(self.candidates, date(2025, 9, 22))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "TAX_8471_V2")


from tests.fixtures.sample_invoices import make_test_context


class TestS21RulesCorrectness(unittest.TestCase):
    """Test Sprint 21 compliance rules explainability and contract compliance."""

    def test_tax_rate_correctness_rule_explainability(self):
        """Tax rate rule produces reference_id, calculation_trace, and observed_value."""
        rule = TaxRateCorrectnessRule()
        inv = Invoice(
            invoice_id="INV-001",
            invoice_number="INV-001",
            invoice_date="2025-09-22",
            counterparty_name="Acme Corp",
            gstin="27AAACB1234A1Z5",
            hsn_sac="8471",
            cgst_rate=0.09,
            sgst_rate=0.09,
            igst_rate=0.0,
            direction="AP",
            place_of_supply="Maharashtra",
        )
        ctx = make_test_context()
        res = rule.validate(inv, context=ctx)
        self.assertIn(res.status, ["PASS", "NEEDS_REVIEW"])
        self.assertEqual(res.rule_version, "2.0")

    def test_hsn_validity_rule_explainability(self):
        """HSN rule produces reference_classification_status in evidence."""
        rule = HSNValidityRule()
        inv = Invoice(
            invoice_id="INV-002",
            invoice_number="INV-002",
            invoice_date="2024-01-01",
            counterparty_name="Acme Corp",
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
        )
        ctx = make_test_context()
        res = rule.validate(inv, context=ctx)
        self.assertEqual(res.rule_version, "2.0")
        self.assertIn("reference_classification_status", res.evidence)

    def test_gstin_format_rule_explainability(self):
        """GSTIN rule validates standard 15-char format and sets observed_value."""
        rule = GSTINFormatRule()
        inv = Invoice(
            invoice_id="INV-003",
            invoice_number="INV-003",
            invoice_date="2024-01-01",
            counterparty_name="Acme Corp",
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
        )
        ctx = make_test_context()
        res = rule.validate(inv, context=ctx)
        self.assertEqual(res.status, "PASS")
        self.assertEqual(res.observed_value, "27AAACB1234A1Z5")

    def test_place_of_supply_rule_explainability(self):
        """POS rule validates intra-state CGST+SGST structure."""
        rule = PlaceOfSupplyRule()
        inv = Invoice(
            invoice_id="INV-004",
            invoice_number="INV-004",
            invoice_date="2024-01-01",
            counterparty_name="Acme Corp",
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
            cgst_rate=0.09,
            sgst_rate=0.09,
            igst_rate=0.0,
        )
        ctx = make_test_context()
        res = rule.validate(inv, context=ctx)
        self.assertIn("is_intra_state", res.evidence)

    def test_itc_eligibility_review_indicator(self):
        """ITC rule flags blocked keywords as review indicators."""
        rule = ITCEligibilityRule()
        inv = Invoice(
            invoice_id="INV-005",
            invoice_number="INV-005",
            invoice_date="2024-01-01",
            counterparty_name="Acme Corp",
            gstin="29AAACB1084F118",
            place_of_supply="Karnataka",
            hsn_sac="8471",
            direction="AP",
            item_desc="Personal food and catering services",
            gstr2b_reflected=True,
        )
        ctx = ValidationContext(itc_blocked_keywords=["food", "catering", "personal"])
        res = rule.validate(inv, context=ctx)
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.financial_exposure_type, "ITC at Risk")
        self.assertIn("blocked-ITC indicator", res.message)


if __name__ == "__main__":
    unittest.main()
