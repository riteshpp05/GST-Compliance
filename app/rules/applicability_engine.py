"""
UC15 GST Compliance Agent — Applicability Engine (Phase 3)
Determines rule applicability (APPLICABLE, NOT_APPLICABLE, UNKNOWN) prior to statutory rule execution.
Prevents non-applicable transactions (e.g., AR Sales checking ITC, or Services checking E-Way Bill) from generating false failures.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict
from pydantic import BaseModel, Field

from app.domain.models.canonical_transaction import CanonicalTransaction


class ApplicabilityStatus(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class RuleApplicabilityResult(BaseModel):
    rule_id: str
    status: ApplicabilityStatus = ApplicabilityStatus.APPLICABLE
    reason: str = "Rule is applicable for transaction context."


class ApplicabilityEngine:
    """
    Applicability Engine.
    Filters rule execution based on transaction direction, supply type, document type, and goods vs services.
    """

    @staticmethod
    def check_applicability(tx: CanonicalTransaction, rule_id: str) -> RuleApplicabilityResult:
        rule_id_upper = rule_id.upper()
        hsn = (tx.hsn_code or tx.sac_code or "").strip()

        # 1. ITC Eligibility Rules (ITC_001, ITC_180_001)
        if "ITC" in rule_id_upper:
            if tx.transaction_type == "OUTWARD_AR":
                return RuleApplicabilityResult(
                    rule_id=rule_id,
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason="ITC rules are NOT APPLICABLE for Outward Sales (AR) transactions.",
                )

        # 2. E-Way Bill Rules (EWB_001, EWAY_001)
        if "EWB" in rule_id_upper or "EWAY" in rule_id_upper:
            # Services (SAC codes starting with 99) do not involve physical goods movement
            if hsn.startswith("99"):
                return RuleApplicabilityResult(
                    rule_id=rule_id,
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason=f"E-Way Bill is NOT APPLICABLE for Service SAC Code '{hsn}'.",
                )

        # 3. Credit / Debit Note Rules (CDN_001)
        if "CDN" in rule_id_upper:
            doc_type = (tx.document_type or "").upper()
            is_cdn_doc = "CDN" in doc_type or "CRN" in doc_type or tx.is_credit_debit_note or tx.taxable_value < 0
            if not is_cdn_doc:
                return RuleApplicabilityResult(
                    rule_id=rule_id,
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason="CDN rules are NOT APPLICABLE for standard Tax Invoices.",
                )

        # 4. Reverse Charge Mechanism Rules (RCM_001)
        if "RCM" in rule_id_upper:
            if not tx.rcm_applicable and not hsn.startswith(("9965", "9983", "7204", "8548", "8549")):
                return RuleApplicabilityResult(
                    rule_id=rule_id,
                    status=ApplicabilityStatus.NOT_APPLICABLE,
                    reason=f"RCM rules are NOT APPLICABLE for standard Forward Charge HSN '{hsn}'.",
                )

        # Default: Rule is applicable
        return RuleApplicabilityResult(
            rule_id=rule_id,
            status=ApplicabilityStatus.APPLICABLE,
            reason="Rule is applicable for transaction context.",
        )
