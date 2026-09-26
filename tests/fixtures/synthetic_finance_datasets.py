"""
UC15 GST Compliance Agent — Synthetic Finance Datasets (Sprint 22)
12 realistic finance investigation scenarios for unit, integration, and AI testing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class SyntheticFinanceScenario:
    scenario_id: str
    title: str
    description: str
    invoice_payload: Dict[str, Any]
    gstr2b_payload: Optional[Dict[str, Any]] = None
    supplier_master_payload: Optional[Dict[str, Any]] = None
    expected_status: str = "NEEDS_REVIEW"
    expected_findings_count: int = 1
    expected_contradictions_count: int = 0
    expected_financial_exposure: Decimal = Decimal("0.00")
    expected_evidence_sufficiency: str = "PARTIALLY_SUFFICIENT"


SYNTHETIC_FINANCE_SCENARIOS: List[SyntheticFinanceScenario] = [
    # 1. Tax Rate Mismatch (Intra-State)
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-01",
        title="Tax Rate Mismatch (18% Charged vs 12% Statutory)",
        description="Supplier charged 18% tax (9% CGST + 9% SGST) on HSN 8471 items which have statutory rate of 12%.",
        invoice_payload={
            "invoice_id": "INV-2026-S01",
            "invoice_date": "2026-03-10",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "TechHardware Pvt Ltd",
            "hsn_code": "8471",
            "taxable_value": 100000.0,
            "cgst_rate": 9.0,
            "sgst_rate": 9.0,
            "igst_rate": 0.0,
            "cgst_amount": 9000.0,
            "sgst_amount": 9000.0,
            "igst_amount": 0.0,
            "total_tax": 18000.0,
            "total_amount": 118000.0,
            "place_of_supply": "27",
            "direction": "AP",
        },
        gstr2b_payload={"taxable_value": 100000.0, "total_tax": 18000.0},
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="NEEDS_REVIEW",
        expected_findings_count=1,
        expected_financial_exposure=Decimal("6000.00"),
        expected_evidence_sufficiency="SUFFICIENT",
    ),

    # 2. Blocked ITC Section 17(5)
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-02",
        title="Blocked ITC Section 17(5) - Motor Vehicle Purchase",
        description="Inward AP invoice for motor vehicle purchase claimed as input tax credit.",
        invoice_payload={
            "invoice_id": "INV-2026-S02",
            "invoice_date": "2026-03-12",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "AutoMotors Sales Pvt Ltd",
            "hsn_code": "8703",
            "taxable_value": 500000.0,
            "igst_rate": 28.0,
            "igst_amount": 140000.0,
            "total_tax": 140000.0,
            "total_amount": 640000.0,
            "place_of_supply": "27",
            "direction": "AP",
        },
        gstr2b_payload={"taxable_value": 500000.0, "total_tax": 140000.0},
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="NEEDS_REVIEW",
        expected_findings_count=1,
        expected_financial_exposure=Decimal("140000.00"),
        expected_evidence_sufficiency="SUFFICIENT",
    ),

    # 3. PoS Tax Head Contradiction
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-03",
        title="Place of Supply Tax Head Contradiction (Inter-state charged as Intra-state)",
        description="Supplier state 27 (MH), Recipient state 29 (KA), PoS 29, but invoice charged CGST+SGST (27).",
        invoice_payload={
            "invoice_id": "INV-2026-S03",
            "invoice_date": "2026-03-14",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "29BBBCB5678D1Z2",
            "supplier_name": "MH Industrial Supplies",
            "hsn_code": "8471",
            "taxable_value": 200000.0,
            "cgst_rate": 9.0,
            "sgst_rate": 9.0,
            "igst_rate": 0.0,
            "cgst_amount": 18000.0,
            "sgst_amount": 18000.0,
            "igst_amount": 0.0,
            "total_tax": 36000.0,
            "total_amount": 236000.0,
            "place_of_supply": "29",
            "direction": "AP",
        },
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="NEEDS_REVIEW",
        expected_contradictions_count=1,
        expected_evidence_sufficiency="PARTIALLY_SUFFICIENT",
    ),

    # 4. Cancelled Supplier Active IRN Contradiction
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-04",
        title="Cancelled Supplier issuing invoice with IRN claim",
        description="Supplier GSTIN status CANCELLED on 2024-01-15, but invoice issued on 2026-03-15.",
        invoice_payload={
            "invoice_id": "INV-2026-S04",
            "invoice_date": "2026-03-15",
            "supplier_gstin": "27DEFGB9999C1Z9",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "Defunct Traders",
            "hsn_code": "8471",
            "taxable_value": 80000.0,
            "igst_rate": 18.0,
            "igst_amount": 14400.0,
            "total_tax": 14400.0,
            "total_amount": 94400.0,
            "irn": "11223344556677889900aabbccddeeff",
            "direction": "AP",
        },
        supplier_master_payload={"status": "CANCELLED", "cancellation_date": "2024-01-15"},
        expected_status="NON_COMPLIANT",
        expected_contradictions_count=1,
        expected_evidence_sufficiency="PARTIALLY_SUFFICIENT",
    ),

    # 5. ERP Paid vs GSTR-2B Missing
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-05",
        title="ERP Paid Invoice Missing in GSTR-2B",
        description="Payment remitted to vendor in ERP, but invoice missing from buyer GSTR-2B statement.",
        invoice_payload={
            "invoice_id": "INV-2026-S05",
            "invoice_date": "2026-02-20",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "Unresponsive Supplier Ltd",
            "hsn_code": "8471",
            "taxable_value": 300000.0,
            "igst_rate": 18.0,
            "igst_amount": 54000.0,
            "total_tax": 54000.0,
            "total_amount": 354000.0,
            "is_paid": True,
            "payment_status": "PAID",
            "is_gstr2b_matched": False,
            "direction": "AP",
        },
        gstr2b_payload=None,
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="NEEDS_REVIEW",
        expected_contradictions_count=1,
        expected_financial_exposure=Decimal("54000.00"),
        expected_evidence_sufficiency="PARTIALLY_SUFFICIENT",
    ),

    # 6. Missing E-Way Bill High Value
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-06",
        title="Missing E-Way Bill for Consignment > 50,000",
        description="High value consignment of INR 250,000 without attached E-Way Bill.",
        invoice_payload={
            "invoice_id": "INV-2026-S06",
            "invoice_date": "2026-03-18",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "Heavy Equipments Corp",
            "hsn_code": "8471",
            "taxable_value": 250000.0,
            "igst_rate": 18.0,
            "igst_amount": 45000.0,
            "total_tax": 45000.0,
            "total_amount": 295000.0,
            "eway_bill_no": None,
            "direction": "AP",
        },
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="NEEDS_REVIEW",
        expected_evidence_sufficiency="PARTIALLY_SUFFICIENT",
    ),

    # 7. E-Invoice IRN Missing
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-07",
        title="Missing E-Invoice IRN Barcode",
        description="B2B sales invoice lacking IRN e-invoice barcode.",
        invoice_payload={
            "invoice_id": "INV-2026-S07",
            "invoice_date": "2026-03-19",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "Global Tech Services",
            "hsn_code": "8471",
            "taxable_value": 150000.0,
            "igst_rate": 18.0,
            "igst_amount": 27000.0,
            "total_tax": 27000.0,
            "total_amount": 177000.0,
            "irn": None,
            "direction": "AR",
        },
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="NEEDS_REVIEW",
        expected_evidence_sufficiency="PARTIALLY_SUFFICIENT",
    ),

    # 8. Effective Date Historical Rate
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-08",
        title="Effective Date Rate Change Boundary",
        description="Transaction date 2025-08-01 evaluated against Version 1 statutory rate schedule.",
        invoice_payload={
            "invoice_id": "INV-2025-S08",
            "invoice_date": "2025-08-01",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "Historical Goods Ltd",
            "hsn_code": "8471",
            "taxable_value": 100000.0,
            "igst_rate": 18.0,
            "igst_amount": 18000.0,
            "total_tax": 18000.0,
            "total_amount": 118000.0,
            "direction": "AP",
        },
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="COMPLIANT",
        expected_evidence_sufficiency="SUFFICIENT",
    ),

    # 9. Arithmetic Rounding Tolerance Pass
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-09",
        title="Arithmetic Line Item Rounding (0.02 INR delta)",
        description="Invoice total differs by 0.02 INR due to line item rounding, within 0.05 tolerance.",
        invoice_payload={
            "invoice_id": "INV-2026-S09",
            "invoice_date": "2026-03-20",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "Precision Tools",
            "hsn_code": "8471",
            "taxable_value": 10000.00,
            "cgst_rate": 9.0,
            "sgst_rate": 9.0,
            "cgst_amount": 900.01,
            "sgst_amount": 900.01,
            "total_tax": 1800.02,
            "total_amount": 11800.02,
            "direction": "AP",
        },
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="COMPLIANT",
        expected_evidence_sufficiency="SUFFICIENT",
    ),

    # 10. Multiple Contradictions Case
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-10",
        title="Multiple Cross-Signal Contradictions Case",
        description="Combined tax head mismatch + missing GSTR-2B + cancelled supplier status.",
        invoice_payload={
            "invoice_id": "INV-2026-S10",
            "invoice_date": "2026-03-21",
            "supplier_gstin": "27DEFGB9999C1Z9",
            "recipient_gstin": "29BBBCB5678D1Z2",
            "supplier_name": "High Risk Vendor Corp",
            "hsn_code": "8471",
            "taxable_value": 500000.0,
            "cgst_rate": 9.0,
            "sgst_rate": 9.0,
            "cgst_amount": 45000.0,
            "sgst_amount": 45000.0,
            "total_tax": 90000.0,
            "total_amount": 590000.0,
            "place_of_supply": "29",
            "is_paid": True,
            "is_gstr2b_matched": False,
            "direction": "AP",
        },
        supplier_master_payload={"status": "CANCELLED", "cancellation_date": "2024-06-01"},
        expected_status="NON_COMPLIANT",
        expected_contradictions_count=3,
        expected_evidence_sufficiency="PARTIALLY_SUFFICIENT",
    ),

    # 11. Fully Compliant Clean Invoice
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-11",
        title="Fully Compliant Clean B2B Invoice",
        description="Valid B2B invoice with exact tax, active GSTIN, GSTR-2B matched, IRN present, EWB present.",
        invoice_payload={
            "invoice_id": "INV-2026-S11",
            "invoice_date": "2026-03-22",
            "supplier_gstin": "27AAACB1234C1Z1",
            "recipient_gstin": "27BBBCB5678D1Z2",
            "supplier_name": "Model Supplier Ltd",
            "hsn_code": "8471",
            "taxable_value": 100000.0,
            "cgst_rate": 9.0,
            "sgst_rate": 9.0,
            "cgst_amount": 9000.0,
            "sgst_amount": 9000.0,
            "total_tax": 18000.0,
            "total_amount": 118000.0,
            "place_of_supply": "27",
            "irn": "99887766554433221100fedcba987654",
            "eway_bill_no": "121234345656",
            "is_gstr2b_matched": True,
            "direction": "AP",
        },
        gstr2b_payload={"taxable_value": 100000.0, "total_tax": 18000.0},
        supplier_master_payload={"status": "ACTIVE"},
        expected_status="COMPLIANT",
        expected_findings_count=0,
        expected_contradictions_count=0,
        expected_financial_exposure=Decimal("0.00"),
        expected_evidence_sufficiency="SUFFICIENT",
    ),

    # 12. Insufficient Data Partial Payload
    SyntheticFinanceScenario(
        scenario_id="S22-SCENARIO-12",
        title="Insufficient Data Payload",
        description="Raw invoice missing taxable value and missing counterparty state details.",
        invoice_payload={
            "invoice_id": "INV-2026-S12",
            "invoice_date": "2026-03-23",
            "supplier_gstin": "",
            "recipient_gstin": "",
            "hsn_code": "",
            "taxable_value": None,
            "total_amount": None,
            "direction": "AP",
        },
        expected_status="NEEDS_REVIEW",
        expected_evidence_sufficiency="INSUFFICIENT",
    ),
]


def get_scenario_by_id(scenario_id: str) -> Optional[SyntheticFinanceScenario]:
    """Retrieve synthetic scenario by ID."""
    for s in SYNTHETIC_FINANCE_SCENARIOS:
        if s.scenario_id == scenario_id:
            return s
    return None
