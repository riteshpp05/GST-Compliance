"""
Unit tests for DataQualityEngine & usability classification.
"""
from decimal import Decimal
from app.domain.models.canonical_transaction import CanonicalTransaction
from app.domain.enums.data_quality_status import DataQualityStatus
from app.rules.data_quality_engine import DataQualityEngine


def test_valid_transaction_data_quality():
    tx = CanonicalTransaction(
        transaction_id="1",
        document_number="INV-001",
        supplier_gstin="27AAACA1234A1Z5",
        taxable_value=Decimal("1000.00"),
    )
    assessment = DataQualityEngine.evaluate(tx)
    assert assessment.overall_status == DataQualityStatus.VALID
    assert assessment.usable_for_statutory_check == True


def test_missing_data_does_not_cause_invalid_rejection():
    tx = CanonicalTransaction(
        transaction_id="2",
        document_number="INV-002",
        supplier_gstin="",  # Missing GSTIN
        taxable_value=Decimal("1000.00"),
        eway_bill_applicable=True,
        eway_bill_number=None,  # EWB data unavailable
    )
    assessment = DataQualityEngine.evaluate(tx)
    assert assessment.overall_status == DataQualityStatus.MISSING
    assert assessment.field_statuses["eway_bill_number"] == DataQualityStatus.UNAVAILABLE
