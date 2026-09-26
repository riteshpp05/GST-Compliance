"""
Unit tests for CanonicalTransaction model & Data Lineage tracking.
"""
from decimal import Decimal
from datetime import date
from app.domain.models.invoice import Invoice
from app.domain.models.canonical_transaction import CanonicalTransaction, DataLineage


def test_canonical_transaction_creation():
    tx = CanonicalTransaction(
        transaction_id="101",
        document_number="INV-2026-001",
        supplier_name="Acme Corp",
        supplier_gstin="27AAACA1234A1Z5",
        taxable_value=Decimal("10000.00"),
        cgst_amount=Decimal("900.00"),
        sgst_amount=Decimal("900.00"),
        tax_rate=Decimal("18.00"),
        hsn_code="8471",
        place_of_supply="Maharashtra",
    )
    assert tx.document_number == "INV-2026-001"
    assert tx.supplier_gstin == "27AAACA1234A1Z5"
    assert tx.taxable_value == Decimal("10000.00")


def test_from_and_to_invoice_converter():
    inv = Invoice(
        invoice_id="202",
        invoice_number="INV-2026-SUPPLY",
        invoice_date="2026-05-15",
        direction="AP",
        counterparty_name="Tech Solutions Ltd",
        gstin="29BBBCC5678B1Z2",
        place_of_supply="Maharashtra",
        hsn_sac="998313",
        taxable_value=Decimal("50000.00"),
        cgst_amount=Decimal("4500.00"),
        sgst_amount=Decimal("4500.00"),
        igst_amount=Decimal("0.00"),
        cgst_rate=Decimal("9.00"),
        sgst_rate=Decimal("9.00"),
    )

    canonical = CanonicalTransaction.from_invoice(inv, source_system="MOCK_LOADER")
    assert canonical.document_number == "INV-2026-SUPPLY"
    assert canonical.supplier_gstin == "29BBBCC5678B1Z2"
    assert canonical.supplier_state == "29"
    assert canonical.lineage["taxable_value"].source_system == "MOCK_LOADER"

    converted_back = canonical.to_invoice()
    assert converted_back.invoice_number == inv.invoice_number
    assert converted_back.gstin == inv.gstin
    assert converted_back.taxable_value == inv.taxable_value
