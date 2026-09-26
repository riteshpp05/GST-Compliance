"""
UC15 GST Compliance Agent — Invoice Normalizer 2.0
Transforms heterogeneous raw records from any source into clean canonical Invoice instances.
Captures data quality warnings and parsing errors without crashing batch execution.
"""
from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union

from app.domain.exceptions import NormalizationError
from app.domain.models.ingestion import (
    IngestionBatchResult,
    IngestionRecordResult,
    IngestionStatus,
    SourceMetadata,
)
from app.domain.models.invoice import Invoice
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

NULL_REPRESENTATIONS = {"", "none", "null", "nan", "n/a", "na", "-", "nil"}


class InvoiceNormalizer:
    """Normalizes raw input records from any adapter into canonical Invoice instances."""

    @staticmethod
    def clean_str(val: Any, default: str = "") -> str:
        """Trim whitespace and map null representations to default."""
        if val is None:
            return default
        s = str(val).strip()
        if s.lower() in NULL_REPRESENTATIONS:
            return default
        return s

    @staticmethod
    def clean_gstin(val: Any) -> str:
        """Normalize GSTIN formatting (strip whitespace, uppercase) without mutating digits."""
        s = InvoiceNormalizer.clean_str(val)
        return s.upper().replace(" ", "").replace("\t", "")

    @staticmethod
    def clean_date(val: Any) -> str:
        """Parse various date formats into canonical ISO YYYY-MM-DD."""
        if val is None:
            return datetime.date.today().isoformat()
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.strftime("%Y-%m-%d")
        
        # Handle Excel serial dates if float/int
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            try:
                # Excel base date usually Dec 30 1899
                dt = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=int(val))
                return dt.strftime("%Y-%m-%d")
            except (ValueError, OverflowError):
                pass

        s = str(val).strip()
        if s.lower() in NULL_REPRESENTATIONS:
            return datetime.date.today().isoformat()

        # Try common human and system formats
        for fmt in (
            "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
            "%d.%m.%Y", "%m/%d/%Y", "%Y%m%d", "%d %b %Y", "%d-%b-%Y"
        ):
            try:
                dt = datetime.datetime.strptime(s, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Fallback cleaned string
        return s

    @staticmethod
    def clean_decimal(val: Any, default: str = "0.00") -> Decimal:
        """Convert arbitrary numeric string/float to precision Decimal."""
        if val is None:
            return Decimal(default)
        if isinstance(val, Decimal):
            return val
        s = str(val).strip().replace(",", "").replace(" ", "").replace("₹", "").replace("Rs.", "")
        if s.lower() in NULL_REPRESENTATIONS:
            return Decimal(default)
        try:
            return Decimal(s)
        except InvalidOperation:
            logger.warning(f"Could not parse decimal from '{val}', falling back to {default}")
            return Decimal(default)

    @classmethod
    def normalize_tax_rate(cls, val: Any, default: str = "0.00") -> Decimal:
        """
        Normalize tax rate to a percentage value (e.g. 9.00 or 18.00).
        If expressed as a decimal fraction like 0.09 or 0.18, normalizes to percentage without distorting whole numbers.
        """
        dec = cls.clean_decimal(val, default=default)
        if dec <= 0:
            return Decimal("0.00")
        fraction_mappings = {
            Decimal("0.03"): Decimal("3.00"),
            Decimal("0.05"): Decimal("5.00"),
            Decimal("0.06"): Decimal("6.00"),
            Decimal("0.09"): Decimal("9.00"),
            Decimal("0.12"): Decimal("12.00"),
            Decimal("0.14"): Decimal("14.00"),
            Decimal("0.18"): Decimal("18.00"),
            Decimal("0.28"): Decimal("28.00"),
        }
        if dec in fraction_mappings:
            return fraction_mappings[dec]
        if Decimal("0.00") < dec < Decimal("1.00") and dec != Decimal("0.25"):
            hundred_val = dec * Decimal("100")
            if hundred_val in {Decimal("3"), Decimal("5"), Decimal("6"), Decimal("9"), Decimal("12"), Decimal("14"), Decimal("18"), Decimal("28")}:
                return hundred_val
        return dec

    @staticmethod
    def clean_bool(val: Any, default: bool = True) -> bool:
        """Convert heterogeneous boolean representations."""
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        s = str(val).strip().upper()
        if s in ("YES", "Y", "TRUE", "1", "T"):
            return True
        if s in ("NO", "N", "FALSE", "0", "F"):
            return False
        return default

    @classmethod
    def normalize_record(
        cls,
        raw_data: Dict[str, Any],
        source_metadata: Optional[SourceMetadata] = None,
        record_index: int = 0,
    ) -> IngestionRecordResult:
        """
        Safely normalize a single record, producing an IngestionRecordResult.
        Never throws unhandled exceptions; categorizes errors into IngestionStatus.
        """
        meta = source_metadata or SourceMetadata(source_type="dict", source_name=f"record_{record_index}")
        errors: List[str] = []
        warnings: List[str] = []

        try:
            inv_no = cls.clean_str(
                raw_data.get("invoice_no")
                or raw_data.get("invoice_number")
                or raw_data.get("invoice_id")
                or raw_data.get("Invoice")
                or raw_data.get("Invoice No")
                or raw_data.get("SupplierInvoice")
                or raw_data.get("BillingDocument")
                or raw_data.get("BELNR")
                or raw_data.get("VBELN")
            )
            if not inv_no:
                errors.append("Missing mandatory invoice identifier (invoice_no/invoice_number/SupplierInvoice)")
                return IngestionRecordResult(
                    record_index=record_index,
                    source_metadata=meta,
                    status=IngestionStatus.INCOMPLETE,
                    raw_data=raw_data,
                    errors=errors,
                    warnings=warnings,
                )

            inv_date = cls.clean_date(
                raw_data.get("invoice_date")
                or raw_data.get("date")
                or raw_data.get("Invoice Date")
                or raw_data.get("InvoiceDate")
                or raw_data.get("BLDAT")
                or raw_data.get("FKDAT")
            )
            direction = cls.clean_str(
                raw_data.get("direction") or raw_data.get("Direction") or ("AP" if "SupplierInvoice" in raw_data else "AR"),
                default="AR"
            ).upper()
            if direction not in ("AR", "AP"):
                warnings.append(f"Unrecognized direction '{direction}', defaulting to AR")
                direction = "AR"

            supplier_gstin = cls.clean_gstin(
                raw_data.get("supplier_gstin")
                or raw_data.get("seller_gstin")
                or raw_data.get("Supplier GSTIN")
                or raw_data.get("VendorGSTIN")
                or raw_data.get("STCD3")
            )
            recipient_gstin = cls.clean_gstin(
                raw_data.get("recipient_gstin")
                or raw_data.get("buyer_gstin")
                or raw_data.get("Recipient GSTIN")
                or raw_data.get("CustomerGSTIN")
            )

            gstin = cls.clean_gstin(
                raw_data.get("counterparty_gstin")
                or raw_data.get("gstin")
                or raw_data.get("Counterparty GSTIN")
                or raw_data.get("GSTIN")
                or (supplier_gstin if direction == "AP" else recipient_gstin)
                or supplier_gstin
                or recipient_gstin
            )
            if not gstin:
                warnings.append("Missing counterparty GSTIN")

            cparty_name = cls.clean_str(
                raw_data.get("counterparty_name")
                or raw_data.get("vendor_name")
                or raw_data.get("customer_name")
                or raw_data.get("Counterparty Name")
                or raw_data.get("Party")
                or raw_data.get("VendorName")
                or raw_data.get("CustomerName")
                or raw_data.get("NAME1")
                or "Unknown Counterparty"
            )
            pos = cls.clean_str(
                raw_data.get("place_of_supply")
                or raw_data.get("pos")
                or raw_data.get("Place of Supply")
                or raw_data.get("PlaceOfSupply")
            )
            hsn = cls.clean_str(
                raw_data.get("hsn_code")
                or raw_data.get("hsn_sac")
                or raw_data.get("hsn")
                or raw_data.get("HSN Code")
                or raw_data.get("HSNCode")
                or raw_data.get("STEUC")
            )
            desc = cls.clean_str(
                raw_data.get("item_desc")
                or raw_data.get("description")
                or raw_data.get("Item Desc")
                or raw_data.get("ItemDescription")
                or raw_data.get("ARKTX")
            )

            raw_taxable = (
                raw_data.get("taxable_value_inr")
                or raw_data.get("taxable_value")
                or raw_data.get("Taxable Value (INR)")
                or raw_data.get("TaxableValue")
                or raw_data.get("WRBTR")
                or raw_data.get("NETWR")
            )
            taxable_val = cls.clean_decimal(raw_taxable)

            cgst_rate = cls.normalize_tax_rate(raw_data.get("cgst_rate") or raw_data.get("CGST %") or raw_data.get("CGSTRate"))
            sgst_rate = cls.normalize_tax_rate(raw_data.get("sgst_rate") or raw_data.get("SGST %") or raw_data.get("SGSTRate"))
            utgst_rate = cls.normalize_tax_rate(
                raw_data.get("utgst_rate")
                or raw_data.get("ugst_rate")
                or raw_data.get("UTGST %")
                or raw_data.get("UGST %")
                or raw_data.get("UTGSTRate")
                or raw_data.get("UGSTRate")
            )
            igst_rate = cls.normalize_tax_rate(raw_data.get("igst_rate") or raw_data.get("IGST %") or raw_data.get("IGSTRate"))
            cess_rate = cls.normalize_tax_rate(
                raw_data.get("cess_rate")
                or raw_data.get("Cess %")
                or raw_data.get("CessRate")
                or raw_data.get("CESS %")
            )

            raw_total = raw_data.get("total_amt") or raw_data.get("total_amount") or raw_data.get("Total Amt") or raw_data.get("TotalAmount") or raw_data.get("reported_total_amount")
            raw_tax = raw_data.get("total_tax_inr") or raw_data.get("total_tax") or raw_data.get("Total Tax (INR)") or raw_data.get("TotalTax") or raw_data.get("reported_total_tax")

            if raw_total is not None and str(raw_total).strip() != "":
                total_amt = cls.clean_decimal(raw_total)
            elif raw_tax is not None and str(raw_tax).strip() != "":
                total_amt = taxable_val + cls.clean_decimal(raw_tax)
            else:
                total_tax = taxable_val * ((cgst_rate + sgst_rate + utgst_rate + igst_rate + cess_rate) / Decimal("100"))
                total_amt = taxable_val + total_tax

            from app.domain.services.transaction_calculator import sanitize_eway_bill_status

            eway_raw = (
                raw_data.get("eway_bill_status")
                or raw_data.get("eway_bill")
                or raw_data.get("E-Way Bill Status")
                or raw_data.get("EWayBillStatus")
            )
            eway = sanitize_eway_bill_status(eway_raw, taxable_value=taxable_val)

            gstr2b = cls.clean_bool(
                raw_data.get("gstr2b_reflected")
                or raw_data.get("gstr2b")
                or raw_data.get("GSTR-2B Reflected")
                or raw_data.get("GSTR2BReflected")
            )

            # Metadata & SAP Provenance Tracking
            rec_metadata = dict(raw_data.get("metadata", {}))
            if "Table" in raw_data:
                rec_metadata["sap_table"] = raw_data["Table"]
            if "Scenario" in raw_data:
                rec_metadata["sap_scenario"] = raw_data["Scenario"]
            if "CompanyCode" in raw_data:
                rec_metadata["sap_company_code"] = raw_data["CompanyCode"]
            if "VendorNumber" in raw_data:
                rec_metadata["sap_vendor"] = raw_data["VendorNumber"]

            seller_state = cls.clean_str(
                raw_data.get("seller_state")
                or raw_data.get("supplier_state")
                or raw_data.get("Seller State")
                or raw_data.get("Supplier State")
            ) or None
            buyer_state = cls.clean_str(
                raw_data.get("buyer_state")
                or raw_data.get("recipient_state")
                or raw_data.get("Buyer State")
                or raw_data.get("Recipient State")
            ) or None

            inv = Invoice.from_record(
                invoice_no=inv_no,
                invoice_date=inv_date,
                direction=direction,
                counterparty_gstin=gstin,
                counterparty_name=cparty_name,
                place_of_supply=pos,
                hsn_code=hsn,
                item_desc=desc,
                taxable_value_inr=taxable_val,
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                utgst_rate=utgst_rate,
                igst_rate=igst_rate,
                cess_rate=cess_rate,
                total_amt=total_amt,
                total_tax=raw_tax,
                eway_bill_status=eway,
                gstr2b_reflected=gstr2b,
                seller_gstin=supplier_gstin,
                buyer_gstin=recipient_gstin,
                seller_state=seller_state,
                buyer_state=buyer_state,
                tax_type=raw_data.get("tax_type"),
                tax_treatment=raw_data.get("tax_treatment"),
                tax_jurisdiction=raw_data.get("tax_jurisdiction"),
                source_metadata=meta.to_dict(),
                metadata=rec_metadata,
            )

            status = IngestionStatus.DATA_QUALITY_WARNING if warnings else IngestionStatus.VALID
            return IngestionRecordResult(
                record_index=record_index,
                source_metadata=meta,
                status=status,
                raw_data=raw_data,
                invoice=inv,
                errors=errors,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Error normalizing record {record_index}: {e}", exc_info=True)
            return IngestionRecordResult(
                record_index=record_index,
                source_metadata=meta,
                status=IngestionStatus.INVALID,
                raw_data=raw_data,
                errors=[str(e)],
                warnings=warnings,
            )

    @classmethod
    def normalize_dict(cls, data: Dict[str, Any]) -> Invoice:
        """
        Normalize a dictionary into a canonical Invoice.
        Raises NormalizationError on mandatory validation failure (Backward Compatibility).
        """
        result = cls.normalize_record(data)
        if not result.is_valid or result.invoice is None:
            err_msg = "; ".join(result.errors) if result.errors else "Failed to normalize invoice row"
            raise NormalizationError(err_msg)
        return result.invoice

    @classmethod
    def normalize_batch(
        cls,
        raw_records: List[Dict[str, Any]],
        source_metadata: Optional[SourceMetadata] = None,
    ) -> IngestionBatchResult:
        """
        Normalize a list of raw dictionary records into an IngestionBatchResult.
        """
        records: List[IngestionRecordResult] = []
        source_name = source_metadata.source_name if source_metadata else "Batch"
        for idx, item in enumerate(raw_records, start=1):
            meta = source_metadata or SourceMetadata(source_type="dict", source_name=f"record_{idx}")
            rec_res = cls.normalize_record(item, source_metadata=meta, record_index=idx)
            records.append(rec_res)

        return IngestionBatchResult(
            source_name=source_name,
            total_records=len(records),
            records=records,
        )

    @classmethod
    def normalize_row_tuple(
        cls,
        row: Tuple[Any, ...],
        source_metadata: Optional[SourceMetadata] = None,
        record_index: int = 0,
    ) -> Invoice:
        """
        Normalize an Excel row tuple into canonical Invoice.
        """
        if len(row) < 13:
            raise NormalizationError(f"Row has insufficient columns: {len(row)} (expected at least 13)")

        if len(row) >= 16:
            raw_dict = {
                "invoice_no": row[0],
                "invoice_date": row[1],
                "direction": row[2],
                "counterparty_gstin": row[3],
                "counterparty_name": row[4],
                "place_of_supply": row[5],
                "hsn_code": row[6],
                "item_desc": row[7],
                "taxable_value_inr": row[8],
                "cgst_rate": row[9],
                "sgst_rate": row[10],
                "igst_rate": row[11],
                "total_tax_inr": row[12],
                "total_amt": row[13],
                "eway_bill_status": row[14] if len(row) > 14 else "",
                "gstr2b_reflected": row[15] if len(row) > 15 else True,
            }
        else:
            raw_dict = {
                "invoice_no": row[0],
                "invoice_date": row[1],
                "direction": row[2],
                "counterparty_gstin": row[3],
                "counterparty_name": row[4],
                "place_of_supply": row[5],
                "hsn_code": row[6],
                "item_desc": row[7],
                "taxable_value_inr": row[8],
                "cgst_rate": row[9],
                "sgst_rate": row[10],
                "igst_rate": row[11],
                "total_amt": row[12],
                "eway_bill_status": row[13] if len(row) > 13 else "",
                "gstr2b_reflected": row[14] if len(row) > 14 else True,
            }
        res = cls.normalize_record(raw_dict, source_metadata=source_metadata, record_index=record_index)
        if not res.is_valid or res.invoice is None:
            err_msg = "; ".join(res.errors) if res.errors else "Failed to normalize row tuple"
            raise NormalizationError(err_msg)
        return res.invoice
