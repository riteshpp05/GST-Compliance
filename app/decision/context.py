"""
UC15 GST Compliance Agent — Universal Decision Context
Canonical representation of all taxpayer, transaction, supply, POS, E-Invoice, E-Way Bill, SAP, and Returns facts.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.domain.models.invoice import Invoice


STATE_CODE_NAME_MAP: Dict[str, str] = {
    "01": "JAMMU AND KASHMIR",
    "02": "HIMACHAL PRADESH",
    "03": "PUNJAB",
    "04": "CHANDIGARH",
    "05": "UTTARAKHAND",
    "06": "HARYANA",
    "07": "DELHI",
    "08": "RAJASTHAN",
    "09": "UTTAR PRADESH",
    "10": "BIHAR",
    "11": "SIKKIM",
    "12": "ARUNACHAL PRADESH",
    "13": "NAGALAND",
    "14": "MANIPUR",
    "15": "MIZORAM",
    "16": "TRIPURA",
    "17": "MEGHALAYA",
    "18": "ASSAM",
    "19": "WEST BENGAL",
    "20": "JHARKHAND",
    "21": "ODISHA",
    "22": "CHATTISGARH",
    "23": "MADHYA PRADESH",
    "24": "GUJARAT",
    "25": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "26": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "27": "MAHARASHTRA",
    "28": "ANDHRA PRADESH",
    "29": "KARNATAKA",
    "30": "GOA",
    "31": "LAKSHADWEEP",
    "32": "KERALA",
    "33": "TAMIL NADU",
    "34": "PUDUCHERRY",
    "35": "ANDAMAN AND NICOBAR ISLANDS",
    "36": "TELANGANA",
    "37": "ANDHRA PRADESH",
    "38": "LADAKH",
    "97": "OTHER TERRITORY",
    "99": "CENTRE JURISDICTION",
}


def normalize_state(state: Optional[str]) -> str:
    if not state:
        return ""
    st = str(state).strip().upper()
    if st in STATE_CODE_NAME_MAP:
        return STATE_CODE_NAME_MAP[st]
    if len(st) <= 2 and st.zfill(2) in STATE_CODE_NAME_MAP:
        return STATE_CODE_NAME_MAP[st.zfill(2)]
    return st


class ComplianceContext(BaseModel):
    """
    Exhaustive canonical decision context for GST compliance, SAP tax determination, and audit evaluation.
    """
    # 1. Taxpayer Facts
    supplier_gstin: str
    recipient_gstin: str
    supplier_state: str
    recipient_state: str
    supplier_registration_status: str = "ACTIVE" # ACTIVE | CANCELLED | SUSPENDED
    recipient_registration_status: str = "ACTIVE"
    supplier_registration_type: str = "REGULAR"  # REGULAR | COMPOSITION | CASUAL | NRTP | ISD | TDS | TCS | UIN | SEZ
    recipient_registration_type: str = "REGULAR"
    aggregate_turnover: Decimal = Field(default=Decimal("0.00"))
    financial_year: str = "2025-26"
    composition_status: bool = False
    uin_status: bool = False
    is_sez_unit: bool = False
    is_sez_developer: bool = False
    is_ecommerce_operator: bool = False
    is_isd: bool = False
    is_casual_taxable_person: bool = False
    is_non_resident_taxable_person: bool = False

    # 2. Transaction & Document Facts
    transaction_date: date
    document_date: date
    posting_date: Optional[date] = None
    supply_type: str = "TAXABLE"  # TAXABLE | EXEMPT | NIL_RATED | ZERO_RATED | NON_GST | OUT_OF_SCOPE
    transaction_type: str = "INTRA_STATE" # INTRA_STATE | INTER_STATE | EXPORT | IMPORT | SEZ
    document_type: str = "INV"  # INV | CRN | DBN | ADVANCE | BILL_OF_SUPPLY | DELIVERY_CHALLAN | JOB_WORK
    invoice_type: str = "B2B"  # B2B | B2C | B2CL | B2CS | EXPORT | SEZ | DEEMED_EXPORT | IMPORT | RCM | ISD
    export_type: Optional[str] = None # WITH_PAYMENT | WITHOUT_PAYMENT_LUT
    import_type: Optional[str] = None # GOODS | SERVICES
    original_document_reference: Optional[str] = None

    # 3. Supply & Financial Facts
    hsn_sac: str
    item_description: str = ""
    quantity: Decimal = Field(default=Decimal("0.00"))
    uqc: str = "OTH"
    taxable_value: Decimal = Field(default=Decimal("0.00"))
    discount: Decimal = Field(default=Decimal("0.00"))
    freight: Decimal = Field(default=Decimal("0.00"))
    other_charges: Decimal = Field(default=Decimal("0.00"))
    cgst_rate: Decimal = Field(default=Decimal("0.00"))
    sgst_rate: Decimal = Field(default=Decimal("0.00"))
    igst_rate: Decimal = Field(default=Decimal("0.00"))
    cess_rate: Decimal = Field(default=Decimal("0.00"))
    cgst_amount: Decimal = Field(default=Decimal("0.00"))
    sgst_amount: Decimal = Field(default=Decimal("0.00"))
    igst_amount: Decimal = Field(default=Decimal("0.00"))
    cess_amount: Decimal = Field(default=Decimal("0.00"))
    total_tax: Decimal = Field(default=Decimal("0.00"))
    invoice_total: Decimal = Field(default=Decimal("0.00"))

    # 4. Place of Supply Facts
    place_of_supply: str
    dispatch_state: Optional[str] = None
    ship_to_state: Optional[str] = None
    bill_to_state: Optional[str] = None
    actual_destination_state: Optional[str] = None
    movement_of_goods: bool = True
    service_category: Optional[str] = None # GENERAL_B2B | IMMOVABLE_PROPERTY | TRANSPORTATION | EVENTS | TELECOM | BANKING | OIDAR

    # 5. E-Invoice Facts
    irn: Optional[str] = None
    irn_status: Optional[str] = None # ACTIVE | CANCELLED | DUPLICATE | INVALID
    irn_generation_date: Optional[date] = None
    irn_cancellation_date: Optional[date] = None
    qr_data: Optional[str] = None
    einvoice_applicable: bool = False

    # 6. E-Way Bill Facts
    eway_bill_no: Optional[str] = None
    eway_status: Optional[str] = None # GENERATED | EXPIRED | CANCELLED | NOT_GENERATED
    movement_mode: str = "ROAD" # ROAD | RAIL | AIR | SHIP
    vehicle_no: Optional[str] = None
    transporter_id: Optional[str] = None
    transport_doc_no: Optional[str] = None
    distance_km: Decimal = Field(default=Decimal("0.00"))
    source_pincode: Optional[str] = None
    destination_pincode: Optional[str] = None
    ewb_generation_datetime: Optional[str] = None
    ewb_valid_until: Optional[str] = None
    is_odc: bool = False
    extension_status: bool = False

    # 7. SAP FI/SD Facts
    company_code: str = "1000"
    fiscal_year: str = "2025"
    accounting_document: Optional[str] = None
    billing_document: Optional[str] = None
    billing_item: int = 10
    material: Optional[str] = None
    gl_account: Optional[str] = None
    vendor: Optional[str] = None
    customer: Optional[str] = None
    sap_tax_code: Optional[str] = None # V1, V2, A1, O1, V3
    sap_condition_type: Optional[str] = None # JOIC, JOIS, JOII, JOCP
    clearing_document: Optional[str] = None
    clearing_date: Optional[date] = None
    payment_status: str = "UNPAID" # UNPAID | PARTIAL | PAID | OVERDUE_180
    due_date: Optional[date] = None

    # 8. GST Returns & IMS Facts
    is_rcm: bool = False
    gstr1_status: Optional[str] = None
    gstr2b_status: Optional[str] = None
    gstr3b_status: Optional[str] = None
    gstr2b_reflected: bool = True
    ims_status: str = "NO_ACTION" # ACCEPTED | REJECTED | PENDING | NO_ACTION

    # Provenance
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_invoice(cls, invoice: Invoice) -> "ComplianceContext":
        """Construct ComplianceContext from canonical Invoice domain model."""
        if invoice.direction == "AP":
            s_gstin = invoice.seller_gstin or invoice.gstin
            r_gstin = invoice.buyer_gstin or "27AAACB1234A1Z5"
        else:
            s_gstin = invoice.seller_gstin or "27AAACG9999A1Z1"
            r_gstin = invoice.buyer_gstin or invoice.gstin

        raw_s_state = invoice.seller_state or (s_gstin[:2] if len(s_gstin) >= 2 else "27")
        raw_r_state = invoice.buyer_state or (r_gstin[:2] if len(r_gstin) >= 2 else "27")

        s_state = normalize_state(raw_s_state)
        r_state = normalize_state(raw_r_state)

        from datetime import datetime
        inv_date = invoice.invoice_date
        if isinstance(inv_date, str):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    inv_date = datetime.strptime(inv_date.strip(), fmt).date()
                    break
                except ValueError:
                    continue
            if isinstance(inv_date, str):
                inv_date = date(2025, 1, 1)

        taxable = invoice.taxable_value
        cgst_a = round((taxable * invoice.cgst_rate) / Decimal("100.00"), 2)
        sgst_a = round((taxable * invoice.sgst_rate) / Decimal("100.00"), 2)
        igst_a = round((taxable * invoice.igst_rate) / Decimal("100.00"), 2)
        cess_a = round((taxable * invoice.cess_rate) / Decimal("100.00"), 2)

        pos_norm = normalize_state(invoice.place_of_supply)

        # Statutory determination under Section 7 & 8 of IGST Act 2017:
        # Supply is Inter-State if Location of Supplier != Place of Supply, or if supplier_state != recipient_state, or IGST charged
        is_inter_pos = bool(pos_norm and s_state and pos_norm != s_state)
        is_inter = float(invoice.igst_rate) > 0 or s_state != r_state or is_inter_pos

        return cls(
            supplier_gstin=s_gstin,
            recipient_gstin=r_gstin,
            supplier_state=s_state,
            recipient_state=r_state,
            supplier_registration_type=invoice.supplier_registration_type,
            recipient_registration_type=invoice.recipient_registration_type,
            aggregate_turnover=invoice.turnover or Decimal("0.00"),
            transaction_date=inv_date,
            document_date=inv_date,
            transaction_type="INTER_STATE" if is_inter else "INTRA_STATE",
            invoice_type=invoice.invoice_type,
            hsn_sac=invoice.hsn_sac,
            item_description=invoice.item_desc,
            quantity=invoice.quantity or Decimal("0.00"),
            taxable_value=taxable,
            cgst_rate=invoice.cgst_rate,
            sgst_rate=invoice.sgst_rate,
            igst_rate=invoice.igst_rate,
            cess_rate=invoice.cess_rate,
            cgst_amount=cgst_a,
            sgst_amount=sgst_a,
            igst_amount=igst_a,
            cess_amount=cess_a,
            total_tax=invoice.total_tax,
            invoice_total=invoice.total_amount,
            place_of_supply=pos_norm or invoice.place_of_supply,
            dispatch_state=s_state,
            ship_to_state=r_state,
            bill_to_state=r_state,
            irn=invoice.irn,
            irn_status=invoice.irn_status,
            eway_bill_no=invoice.eway_bill_no or invoice.eway_bill_number,
            eway_status=invoice.eway_bill_status or invoice.eway_bill,
            movement_mode=invoice.movement_mode,
            distance_km=invoice.distance_km or Decimal("0.00"),
            is_odc=invoice.is_odc,
            gl_account=invoice.gl_account,
            sap_tax_code=invoice.sap_tax_code,
            sap_condition_type=invoice.sap_condition_type,
            clearing_document=invoice.clearing_document,
            payment_status=invoice.payment_status or "UNPAID",
            is_rcm=bool(invoice.is_rcm),
            gstr2b_reflected=getattr(invoice, "gstr2b_reflected", True),
            metadata=invoice.metadata or {},
        )
