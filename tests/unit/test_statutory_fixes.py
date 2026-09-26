"""
Unit tests for Step 4 Statutory Consistency Fixes (pos.py and tax.py).
"""
from decimal import Decimal
from app.domain.models.invoice import Invoice
from app.rules.existing.pos import PlaceOfSupplyRule
from app.rules.existing.tax import TaxRateCorrectnessRule
from app.domain.enums.validation_status import ValidationStatus
from app.rules.context import ValidationContext


def test_pos_sez_unit_clean_match():
    inv = Invoice(
        invoice_id="POS-SEZ-1",
        invoice_number="INV-SEZ-001",
        invoice_date="2026-05-10",
        direction="AR",
        invoice_type="SEZ",
        counterparty_name="SEZ Unit Tech Park",
        gstin="24AAACA1234A1Z5",  # 24 = Gujarat
        place_of_supply="SEZ Unit Gujarat",
        hsn_sac="8471",
        taxable_value=Decimal("100000.00"),
        igst_rate=Decimal("0.00"),
        cgst_rate=Decimal("0.00"),
        sgst_rate=Decimal("0.00"),
    )
    ctx = ValidationContext()
    rule = PlaceOfSupplyRule()
    res = rule.validate(inv, context=ctx)
    assert res.status == ValidationStatus.PASS
    assert res.evidence["is_intra_state"] == False


def test_tax_exempt_zero_rate_pass():
    inv = Invoice(
        invoice_id="TAX-EXEMPT-1",
        invoice_number="INV-EXEMPT-001",
        invoice_date="2026-05-10",
        direction="AP",
        invoice_type="EXEMPT",
        counterparty_name="Agriculture Supplier",
        gstin="27AAACA1234A1Z5",
        place_of_supply="Maharashtra",
        hsn_sac="0101",  # Exempt HSN
        taxable_value=Decimal("5000.00"),
        cgst_rate=Decimal("0.00"),
        sgst_rate=Decimal("0.00"),
        igst_rate=Decimal("0.00"),
    )
    ctx = ValidationContext()
    rule = TaxRateCorrectnessRule()
    res = rule.validate(inv, context=ctx)
    assert res.status == ValidationStatus.PASS
    assert res.evidence["rate_matched"] == True
