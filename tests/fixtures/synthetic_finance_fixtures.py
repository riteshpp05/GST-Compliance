"""
UC15 GST Compliance Agent — Synthetic Finance Test Fixtures (Invoices 1 to 20)
Fixtures matching all 20 specific statutory & SAP compliance test scenarios required by enterprise specifications.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List
from app.domain.models.invoice import Invoice


def get_synthetic_finance_fixtures() -> List[Invoice]:
    """
    Constructs all 20 synthetic finance invoice scenarios.
    """
    return [
        # Invoice 1: Normal compliant intra-state invoice
        Invoice.from_record(
            invoice_no="INV-FIN-001",
            invoice_date="2025-05-10",
            direction="AR",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Acme Tech Solutions Pvt Ltd",
            place_of_supply="Maharashtra",
            hsn_code="84713010",
            item_desc="Laptops and Notebooks",
            taxable_value_inr=100000.00,
            cgst_rate=9.00,
            sgst_rate=9.00,
            igst_rate=0.00,
            total_amt=118000.00,
            eway_bill_status="GENERATED",
            irn="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
        ),

        # Invoice 2: Wrong GST rate (Charged 12% instead of statutory 18% for HSN 8471)
        Invoice.from_record(
            invoice_no="INV-FIN-002",
            invoice_date="2025-05-11",
            direction="AR",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Beta Systems Ltd",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="Computer Servers",
            taxable_value_inr=100000.00,
            cgst_rate=6.00,
            sgst_rate=6.00,
            igst_rate=0.00,
            total_amt=112000.00,
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
        ),

        # Invoice 3: Wrong SAP tax code (Configured V1 (IGST 18%) on Intra-state transaction)
        Invoice(
            invoice_id="INV-FIN-003",
            invoice_number="INV-FIN-003",
            invoice_date="2025-05-12",
            direction="AP",
            counterparty_name="Gamma Supplies",
            gstin="27AAACG9999A1Z1",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
            seller_state="27",
            buyer_state="27",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
            taxable_value=Decimal("100000.00"),
            cgst_rate=Decimal("9.00"),
            sgst_rate=Decimal("9.00"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("18000.00"),
            total_amount=Decimal("118000.00"),
            sap_tax_code="V1", # V1 is IGST 18% but transaction is intra-state (should be V2)
        ),

        # Invoice 4: Wrong POS (Declared POS = Delhi for Maharashtra buyer & seller, charged CGST+SGST)
        Invoice.from_record(
            invoice_no="INV-FIN-004",
            invoice_date="2025-05-13",
            direction="AR",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Delta Enterprises",
            place_of_supply="Delhi", # Wrong POS
            hsn_code="8471",
            item_desc="Peripherals",
            taxable_value_inr=50000.00,
            cgst_rate=9.00,
            sgst_rate=9.00,
            igst_rate=0.00, # Should be IGST for interstate supply to Delhi
            total_amt=59000.00,
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
        ),

        # Invoice 5: Missing/invalid IRN (B2B invoice > 5 Cr without IRN)
        Invoice(
            invoice_id="INV-FIN-005",
            invoice_number="INV-FIN-005",
            invoice_date="2025-05-14",
            direction="AR",
            counterparty_name="Epsilon Logistics",
            gstin="07AAACE5555E1Z9",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="07AAACE5555E1Z9",
            place_of_supply="Delhi",
            hsn_sac="8471",
            taxable_value=Decimal("200000.00"),
            cgst_rate=Decimal("0.00"),
            sgst_rate=Decimal("0.00"),
            igst_rate=Decimal("18.00"),
            total_tax=Decimal("36000.00"),
            total_amount=Decimal("236000.00"),
            turnover=Decimal("100000000.00"), # 10 Cr turnover
            irn=None, # Missing IRN
        ),

        # Invoice 6: Expired EWB
        Invoice.from_record(
            invoice_no="INV-FIN-006",
            invoice_date="2025-05-15",
            direction="AR",
            counterparty_gstin="07AAACE5555E1Z9",
            counterparty_name="Zeta Logistics",
            place_of_supply="Delhi",
            hsn_code="8471",
            item_desc="Hardware",
            taxable_value_inr=150000.00,
            cgst_rate=0.00,
            sgst_rate=0.00,
            igst_rate=18.00,
            total_amt=177000.00,
            eway_bill_status="EXPIRED",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="07AAACE5555E1Z9",
        ),

        # Invoice 7: State-specific EWB threshold edge case (Intra-state Maharashtra Rs. 1,00,000 threshold)
        Invoice.from_record(
            invoice_no="INV-FIN-007",
            invoice_date="2025-05-16",
            direction="AR",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Eta Retailers",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="Accessories",
            taxable_value_inr=75000.00, # Above 50k national threshold, below 100k MH threshold
            cgst_rate=9.00,
            sgst_rate=9.00,
            igst_rate=0.00,
            total_amt=88500.00,
            eway_bill_status="NOT_GENERATED",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
        ),

        # Invoice 8: RCM transaction (GTA Services HSN 9965)
        Invoice(
            invoice_id="INV-FIN-008",
            invoice_number="INV-FIN-008",
            invoice_date="2025-05-17",
            direction="AP",
            counterparty_name="Speedy Transport Agency",
            gstin="27AAACT8888T1Z2",
            seller_gstin="27AAACT8888T1Z2",
            buyer_gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="9965", # GTA
            item_desc="Freight charges",
            taxable_value=Decimal("50000.00"),
            cgst_rate=Decimal("2.50"),
            sgst_rate=Decimal("2.50"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("2500.00"),
            total_amount=Decimal("52500.00"),
            is_rcm=True,
            rcm_liability=Decimal("2500.00"),
        ),

        # Invoice 9: Credit note (Table 9B reduction)
        Invoice(
            invoice_id="INV-FIN-009",
            invoice_number="CRN-FIN-009",
            invoice_date="2025-05-18",
            direction="AR",
            counterparty_name="Acme Tech Solutions Pvt Ltd",
            gstin="27AAACB1234A1Z5",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
            taxable_value=Decimal("-20000.00"),
            cgst_rate=Decimal("9.00"),
            sgst_rate=Decimal("9.00"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("-3600.00"),
            total_amount=Decimal("-23600.00"),
            original_invoice_no="INV-FIN-001",
            credit_debit_note_type="CREDIT_NOTE",
        ),

        # Invoice 10: Invoice unpaid beyond 180 days (Unpaid age = 210 days)
        Invoice(
            invoice_id="INV-FIN-010",
            invoice_number="INV-FIN-010",
            invoice_date="2024-10-01", # > 180 days from 2025-05-20
            direction="AP",
            counterparty_name="Iota Components",
            gstin="27AAACI1111I1Z4",
            seller_gstin="27AAACI1111I1Z4",
            buyer_gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
            taxable_value=Decimal("100000.00"),
            cgst_rate=Decimal("9.00"),
            sgst_rate=Decimal("9.00"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("18000.00"),
            total_amount=Decimal("118000.00"),
            payment_status="OVERDUE_180",
            paid_amount=Decimal("0.00"),
            unpaid_amount=Decimal("118000.00"),
            itc_reversal_amount=Decimal("18000.00"),
            interest_amount=Decimal("1479.45"), # 18% p.a. for 30 overdue days
        ),

        # Invoice 11: Partially paid invoice (Paid Rs. 59,000 out of Rs. 118,000)
        Invoice(
            invoice_id="INV-FIN-011",
            invoice_number="INV-FIN-011",
            invoice_date="2024-10-01",
            direction="AP",
            counterparty_name="Kappa Spares",
            gstin="27AAACK2222K1Z3",
            seller_gstin="27AAACK2222K1Z3",
            buyer_gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
            taxable_value=Decimal("100000.00"),
            cgst_rate=Decimal("9.00"),
            sgst_rate=Decimal("9.00"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("18000.00"),
            total_amount=Decimal("118000.00"),
            payment_status="PARTIAL",
            paid_amount=Decimal("59000.00"),
            unpaid_amount=Decimal("59000.00"),
            itc_reversal_amount=Decimal("9000.00"), # 50% proportionate reversal
        ),

        # Invoice 12: 17(5) blocked credit (Outdoor Catering HSN 9963)
        Invoice.from_record(
            invoice_no="INV-FIN-012",
            invoice_date="2025-05-19",
            direction="AP",
            counterparty_gstin="27AAACL3333L1Z2",
            counterparty_name="Lambda Caterers",
            place_of_supply="Maharashtra",
            hsn_code="9963", # Catering
            item_desc="Corporate Event Catering",
            taxable_value_inr=50000.00,
            cgst_rate=9.00,
            sgst_rate=9.00,
            igst_rate=0.00,
            total_amt=59000.00,
            seller_gstin="27AAACL3333L1Z2",
            buyer_gstin="27AAACB1234A1Z5",
        ),

        # Invoice 13: GSTR-2B mismatch (Unreflected AP invoice)
        Invoice.from_record(
            invoice_no="INV-FIN-013",
            invoice_date="2025-05-20",
            direction="AP",
            counterparty_gstin="27AAACM4444M1Z1",
            counterparty_name="Mu Electronics",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="RAM modules",
            taxable_value_inr=80000.00,
            cgst_rate=9.00,
            sgst_rate=9.00,
            igst_rate=0.00,
            total_amt=94400.00,
            gstr2b_reflected=False, # Unreflected in 2B
            seller_gstin="27AAACM4444M1Z1",
            buyer_gstin="27AAACB1234A1Z5",
        ),

        # Invoice 14: Duplicate invoice (Exact match to INV-FIN-001)
        Invoice.from_record(
            invoice_no="INV-FIN-001", # Duplicate number
            invoice_date="2025-05-10",
            direction="AR",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Acme Tech Solutions Pvt Ltd",
            place_of_supply="Maharashtra",
            hsn_code="84713010",
            item_desc="Laptops and Notebooks",
            taxable_value_inr=100000.00,
            cgst_rate=9.00,
            sgst_rate=9.00,
            igst_rate=0.00,
            total_amt=118000.00,
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
        ),

        # Invoice 15: GSTR-1 / GSTR-3B mismatch
        Invoice(
            invoice_id="INV-FIN-015",
            invoice_number="INV-FIN-015",
            invoice_date="2025-05-21",
            direction="AR",
            counterparty_name="Nu Distributors",
            gstin="27AAACN5555N1Z0",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACN5555N1Z0",
            place_of_supply="Maharashtra",
            hsn_sac="8471",
            taxable_value=Decimal("300000.00"),
            cgst_rate=Decimal("9.00"),
            sgst_rate=Decimal("9.00"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("54000.00"),
            total_amount=Decimal("354000.00"),
            gstr1_status="FILED",
            gstr3b_status="UNMATCHED", # Mismatch between 1 and 3B
        ),

        # Invoice 16: SEZ supply (Zero-rated supply with LUT/Bond)
        Invoice.from_record(
            invoice_no="INV-FIN-016",
            invoice_date="2025-05-22",
            direction="AR",
            counterparty_gstin="27AAACS6666S1Z9",
            counterparty_name="Xi SEZ Developers Pvt Ltd",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="IT Infrastructure Supply to SEZ Unit",
            taxable_value_inr=500000.00,
            cgst_rate=0.00,
            sgst_rate=0.00,
            igst_rate=0.00, # Zero rated
            total_amt=500000.00,
            invoice_type="SEZ",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACS6666S1Z9",
        ),

        # Invoice 17: Export (Zero-rated export of services / goods)
        Invoice.from_record(
            invoice_no="INV-FIN-017",
            invoice_date="2025-05-23",
            direction="AR",
            counterparty_gstin="9925FOR9999F1Z0",
            counterparty_name="Omicron International LLC (USA)",
            place_of_supply="Overseas",
            hsn_code="998311",
            item_desc="Software Development Export Services",
            taxable_value_inr=1000000.00,
            cgst_rate=0.00,
            sgst_rate=0.00,
            igst_rate=0.00, # Zero-rated export
            total_amt=1000000.00,
            invoice_type="EXPORT",
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="9925FOR9999F1Z0",
        ),

        # Invoice 18: E-Waste / special HSN (HSN 8548 subject to special RCM)
        Invoice(
            invoice_id="INV-FIN-018",
            invoice_number="INV-FIN-018",
            invoice_date="2025-05-24",
            direction="AP",
            counterparty_name="Pi Recycling Services",
            gstin="27AAACP7777P1Z8",
            seller_gstin="27AAACP7777P1Z8",
            buyer_gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8548", # E-Waste
            taxable_value=Decimal("40000.00"),
            cgst_rate=Decimal("9.00"),
            sgst_rate=Decimal("9.00"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("7200.00"),
            total_amount=Decimal("47200.00"),
            is_rcm=True,
            rcm_liability=Decimal("7200.00"),
        ),

        # Invoice 19: Scrap transaction (Metal scrap HSN 7204 RCM)
        Invoice(
            invoice_id="INV-FIN-019",
            invoice_number="INV-FIN-019",
            invoice_date="2025-05-25",
            direction="AP",
            counterparty_name="Rho Scrap Traders",
            gstin="27AAACR8888R1Z7",
            seller_gstin="27AAACR8888R1Z7",
            buyer_gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="7204", # Metal scrap
            taxable_value=Decimal("60000.00"),
            cgst_rate=Decimal("9.00"),
            sgst_rate=Decimal("9.00"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("10800.00"),
            total_amount=Decimal("70800.00"),
            is_rcm=True,
            rcm_liability=Decimal("10800.00"),
        ),

        # Invoice 20: Historical transaction where statutory policy changed (Tax rate shift in 2025)
        Invoice.from_record(
            invoice_no="INV-FIN-020",
            invoice_date="2023-01-15", # Historical date
            direction="AR",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Sigma Systems",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="Historical IT Equipment Sale",
            taxable_value_inr=100000.00,
            cgst_rate=9.00,
            sgst_rate=9.00,
            igst_rate=0.00,
            total_amt=118000.00,
            seller_gstin="27AAACG9999A1Z1",
            buyer_gstin="27AAACB1234A1Z5",
        ),
    ]
