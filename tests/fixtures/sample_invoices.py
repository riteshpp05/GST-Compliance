"""
Test fixtures providing sample canonical invoices and reference master data.
"""
from decimal import Decimal
from typing import Optional
from app.domain.models.invoice import Invoice
from app.domain.models.tax import HSNMaster
from app.rules.context import ValidationContext

SAMPLE_HSN_MASTER = {
    "8409": HSNMaster.from_raw("8409", "Parts for Internal Combustion Engines", 9, 9, 18),
    "8483": HSNMaster.from_raw("8483", "Transmission Shafts & Cranks", 9, 9, 18),
    "8708": HSNMaster.from_raw("8708", "Motor Vehicle Parts & Accessories", 14, 14, 28),
}

SAMPLE_STATE_REF = {
    "27": "Maharashtra",
    "07": "Delhi",
    "29": "Karnataka",
    "33": "Tamil Nadu",
}


def make_test_context() -> ValidationContext:
    from datetime import date
    from app.reference.services.reference_service import ReferenceService
    from app.reference.models.ewb_policy import EWBPolicyReference
    from app.reference.models.itc_policy import ITCPolicyReference

    ref_service = ReferenceService(auto_load=False)
    ref_service.repository.add_ewb_policy(
        EWBPolicyReference(
            reference_id="SAMPLE_EWB_NATIONAL",
            version="1.0-sample",
            effective_from=date(2017, 7, 1),
            state_code="NATIONAL",
            interstate_threshold=Decimal("50000"),
            intrastate_threshold=Decimal("50000"),
            source="LEGACY_ADAPTED",
        )
    )
    ref_service.repository.add_itc_policy(
        ITCPolicyReference(
            policy_id="SAMPLE_ITC_17_5",
            version="1.0-sample",
            effective_from=date(2017, 7, 1),
            category="BLOCKED_17_5",
            blocked_keywords=["employee welfare", "catering", "food and beverage"],
            is_blocked_17_5=True,
            source="LEGACY_ADAPTED",
        )
    )

    return ValidationContext(
        hsn_master=SAMPLE_HSN_MASTER,
        state_ref=SAMPLE_STATE_REF,
        eway_bill_threshold=Decimal("50000"),
        rate_tolerance_pct=Decimal("0.01"),
        itc_blocked_keywords=["employee welfare", "catering", "food and beverage"],
        reference_service=ref_service,
    )


def make_test_invoice(
    invoice_no: str = "INV-TEST-001",
    invoice_date: str = "2026-03-01",
    direction: str = "AR",
    gstin: str = "27AAACB1234A1Z5",
    counterparty_name: str = "Bosch India Ltd",
    place_of_supply: str = "Maharashtra",
    hsn_code: str = "8409",
    item_desc: str = "Engine parts supply per contract",
    taxable_value: float = 35000.0,
    cgst_rate: float = 9.0,
    sgst_rate: float = 9.0,
    igst_rate: float = 0.0,
    total_amt: Optional[float] = None,
    eway_bill: str = "",
    gstr2b_reflected: bool = True,
    invoice_id: Optional[str] = None,
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
        eway_bill_status=eway_bill,
        gstr2b_reflected=gstr2b_reflected,
        invoice_id=invoice_id,
    )
