"""
Unit tests for ApplicabilityEngine transaction filtering.
"""
from decimal import Decimal
from app.domain.models.canonical_transaction import CanonicalTransaction
from app.rules.applicability_engine import ApplicabilityEngine, ApplicabilityStatus


def test_itc_not_applicable_for_ar_sales():
    tx = CanonicalTransaction(
        transaction_id="1",
        document_number="INV-AR-001",
        transaction_type="OUTWARD_AR",
        taxable_value=Decimal("10000.00"),
    )
    result = ApplicabilityEngine.check_applicability(tx, "ITC_001")
    assert result.status == ApplicabilityStatus.NOT_APPLICABLE
    assert "NOT APPLICABLE for Outward Sales" in result.reason


def test_eway_bill_not_applicable_for_services():
    tx = CanonicalTransaction(
        transaction_id="2",
        document_number="INV-SRV-001",
        hsn_code="998313",  # IT Consulting Service SAC
        taxable_value=Decimal("100000.00"),
    )
    result = ApplicabilityEngine.check_applicability(tx, "EWAY_001")
    assert result.status == ApplicabilityStatus.NOT_APPLICABLE
    assert "NOT APPLICABLE for Service SAC Code" in result.reason
