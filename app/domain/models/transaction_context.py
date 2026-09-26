"""
UC15 GST Compliance Agent — Canonical Transaction Context Domain Model (v3.0)
Normalized representation of transaction facts extracted prior to statutory gate evaluation.
Disambiguates scope, direction, supply category, party identity, and tax breakdown without forcing legal outcomes.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TransactionScope(str, Enum):
    DOMESTIC = "DOMESTIC"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    SEZ = "SEZ"
    DEEMED_EXPORT = "DEEMED_EXPORT"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class TransactionDirection(str, Enum):
    INWARD = "INWARD"   # AP
    OUTWARD = "OUTWARD" # AR


class SupplyCategory(str, Enum):
    GOODS = "GOODS"
    SERVICES = "SERVICES"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class TransactionContext(BaseModel):
    """
    Normalized factual context of a transaction.
    Purely descriptive facts used by the Statutory Checkpoint Engine to evaluate applicability and rules.
    """
    scope: TransactionScope = TransactionScope.DOMESTIC
    direction: TransactionDirection = TransactionDirection.OUTWARD
    category: SupplyCategory = SupplyCategory.GOODS
    invoice_type: str = "B2B"

    # Parties & States
    supplier_gstin: Optional[str] = None
    buyer_gstin: Optional[str] = None
    supplier_state: Optional[str] = None
    buyer_state: Optional[str] = None
    place_of_supply: str = ""

    is_foreign_supplier: bool = False
    is_foreign_buyer: bool = False
    is_intra_state: bool = False

    @property
    def is_foreign_counterparty(self) -> bool:
        return self.is_foreign_supplier or self.is_foreign_buyer or self.scope in (TransactionScope.IMPORT, TransactionScope.EXPORT)

    @property
    def is_export(self) -> bool:
        return self.scope == TransactionScope.EXPORT

    @property
    def is_import(self) -> bool:
        return self.scope == TransactionScope.IMPORT

    @property
    def is_sez(self) -> bool:
        return self.scope == TransactionScope.SEZ

    # Classification
    hsn_sac: str = ""
    item_description: str = ""

    # Financial Facts
    taxable_value: float = 0.0
    applied_cgst_rate: float = 0.0
    applied_sgst_rate: float = 0.0
    applied_utgst_rate: float = 0.0
    applied_igst_rate: float = 0.0
    applied_cess_rate: float = 0.0
    applied_total_rate: float = 0.0

    applied_cgst_amount: float = 0.0
    applied_sgst_amount: float = 0.0
    applied_utgst_amount: float = 0.0
    applied_igst_amount: float = 0.0
    applied_cess_amount: float = 0.0
    applied_total_tax: float = 0.0
    total_amount: float = 0.0

    # Tax Classification Metadata
    tax_treatment: Optional[str] = None
    tax_jurisdiction: Optional[str] = None

    @property
    def applied_ugst_rate(self) -> float:
        return self.applied_utgst_rate

    @property
    def applied_ugst_amount(self) -> float:
        return self.applied_utgst_amount

    # Raw metadata reference
    source_provenance: Optional[Dict[str, Any]] = None

    @classmethod
    def from_invoice(cls, invoice: Any) -> "TransactionContext":
        """Construct normalized TransactionContext from canonical Invoice model."""
        inv_type = getattr(invoice, "invoice_type", "B2B").upper()
        dir_str = str(getattr(invoice, "direction", "AR")).upper()
        direction = TransactionDirection.INWARD if dir_str == "AP" else TransactionDirection.OUTWARD

        # Scope Detection
        if inv_type in ("EXPORT", "DEEMED_EXPORT"):
            scope = TransactionScope.EXPORT
        elif inv_type in ("IMPORT", "SEZ"):
            scope = TransactionScope.SEZ if inv_type == "SEZ" else TransactionScope.IMPORT
        else:
            scope = TransactionScope.DOMESTIC

        # Category Detection (Services vs Goods based on SAC 99 prefix or HSN length/words)
        hsn_sac_str = str(getattr(invoice, "hsn_code", getattr(invoice, "hsn_sac", ""))).strip()
        desc_str = str(getattr(invoice, "item_desc", "")).strip().lower()

        if hsn_sac_str.startswith("99") or "service" in desc_str or "consulting" in desc_str or "maintenance" in desc_str:
            category = SupplyCategory.SERVICES
        elif hsn_sac_str:
            category = SupplyCategory.GOODS
        else:
            category = SupplyCategory.UNKNOWN

        # Parties & States
        supp_gstin = str(getattr(invoice, "seller_gstin", "") or "").strip().upper()
        buy_gstin = str(getattr(invoice, "buyer_gstin", "") or "").strip().upper()
        cparty_gstin = str(getattr(invoice, "gstin", getattr(invoice, "counterparty_gstin", ""))).strip().upper()

        if not supp_gstin:
            supp_gstin = cparty_gstin if direction == TransactionDirection.INWARD else ""
        if not buy_gstin:
            buy_gstin = cparty_gstin if direction == TransactionDirection.OUTWARD else ""

        pos_declared = str(getattr(invoice, "place_of_supply", "")).strip()

        supp_state = str(getattr(invoice, "seller_state", "") or "").strip()
        buy_state = str(getattr(invoice, "buyer_state", "") or "").strip()

        from app.rules.tax_treatment import lookup_state_info
        supp_info = lookup_state_info(supp_gstin[:2]) if (len(supp_gstin) >= 2 and supp_gstin[:2].isdigit()) else lookup_state_info(supp_state)
        pos_info = lookup_state_info(pos_declared)

        is_foreign_supp = len(supp_gstin) < 15 and scope in (TransactionScope.IMPORT, TransactionScope.EXPORT)
        is_foreign_buy = len(buy_gstin) < 15 and scope in (TransactionScope.EXPORT, TransactionScope.SEZ)

        # Intra-state calculation: Supplier State vs Place of Supply
        if scope != TransactionScope.DOMESTIC:
            is_intra = False
        elif supp_info and pos_info:
            is_intra = supp_info.code == pos_info.code
        elif supp_state and pos_declared:
            s_clean = supp_state.lower().replace("sez", "").strip()
            p_clean = pos_declared.lower().replace("sez", "").strip()
            is_intra = (s_clean == p_clean or s_clean in p_clean or p_clean in s_clean)
        else:
            is_intra = False

        # Financials
        taxable = float(getattr(invoice, "taxable_value", getattr(invoice, "taxable_value_inr", 0.0)))
        cgst_r = float(getattr(invoice, "cgst_rate", 0.0))
        sgst_r = float(getattr(invoice, "sgst_rate", 0.0))
        utgst_r = float(getattr(invoice, "utgst_rate", getattr(invoice, "ugst_rate", 0.0)))
        igst_r = float(getattr(invoice, "igst_rate", 0.0))
        cess_r = float(getattr(invoice, "cess_rate", 0.0))

        # Rates clean
        cgst_pct = cgst_r * 100.0 if (0.0 < cgst_r <= 1.0) else cgst_r
        sgst_pct = sgst_r * 100.0 if (0.0 < sgst_r <= 1.0) else sgst_r
        utgst_pct = utgst_r * 100.0 if (0.0 < utgst_r <= 1.0) else utgst_r
        igst_pct = igst_r * 100.0 if (0.0 < igst_r <= 1.0) else igst_r
        cess_pct = cess_r * 100.0 if (0.0 < cess_r <= 1.0) else cess_r

        tot_rates = cgst_pct + sgst_pct + utgst_pct + igst_pct + cess_pct

        tot_tax = float(getattr(invoice, "total_tax", 0.0))
        tot_amt = float(getattr(invoice, "total_amount", getattr(invoice, "total_amt", 0.0)))

        if tot_amt <= 0 and taxable > 0:
            tot_tax = round(taxable * (tot_rates / 100.0), 2)
            tot_amt = taxable + tot_tax
        elif tot_tax <= 0 and tot_amt > taxable:
            tot_tax = tot_amt - taxable

        cgst_amount = float(getattr(invoice, "cgst_amount", round(taxable * (cgst_pct / 100.0), 2)))
        sgst_amount = float(getattr(invoice, "sgst_amount", round(taxable * (sgst_pct / 100.0), 2)))
        utgst_amount = float(getattr(invoice, "utgst_amount", getattr(invoice, "ugst_amount", round(taxable * (utgst_pct / 100.0), 2))))
        igst_amount = float(getattr(invoice, "igst_amount", round(taxable * (igst_pct / 100.0), 2)))
        cess_amount = float(getattr(invoice, "cess_amount", round(taxable * (cess_pct / 100.0), 2)))

        return cls(
            scope=scope,
            direction=direction,
            category=category,
            invoice_type=inv_type,
            supplier_gstin=supp_gstin,
            buyer_gstin=buy_gstin,
            supplier_state=supp_state or (supp_info.name if supp_info else pos_declared),
            buyer_state=buy_state or pos_declared,
            place_of_supply=pos_declared,
            is_foreign_supplier=is_foreign_supp,
            is_foreign_buyer=is_foreign_buy,
            is_intra_state=is_intra,
            hsn_sac=hsn_sac_str,
            item_description=desc_str,
            taxable_value=taxable,
            applied_cgst_rate=cgst_pct,
            applied_sgst_rate=sgst_pct,
            applied_utgst_rate=utgst_pct,
            applied_igst_rate=igst_pct,
            applied_cess_rate=cess_pct,
            applied_total_rate=tot_rates,
            applied_cgst_amount=cgst_amount,
            applied_sgst_amount=sgst_amount,
            applied_utgst_amount=utgst_amount,
            applied_igst_amount=igst_amount,
            applied_cess_amount=cess_amount,
            applied_total_tax=tot_tax,
            total_amount=tot_amt,
            tax_treatment=getattr(invoice, "tax_treatment", None),
            tax_jurisdiction=getattr(invoice, "tax_jurisdiction", None),
        )

