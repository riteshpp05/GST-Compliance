"""
UC15 GST Compliance Agent — Financial Adjustment Models (Sprint 6)
Models for recommended accounting / ledger reconciliations based on quantified tax discrepancies.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict


@dataclass
class FinancialAdjustment:
    """
    Actionable accounting adjustment suggestion derived deterministically from financial impact.
    """
    adjustment_id: str
    invoice_id: str
    adjustment_type: str  # CREDIT_NOTE_REQUIRED | DEBIT_NOTE_REQUIRED | ITC_REVERSAL_REQUIRED | NONE
    suggested_amount: Decimal = Decimal("0.00")
    reason: str = ""
    counterparty_id: str = ""
    reference_rule: str = ""
    action_owner: str = ""
    statutory_provision: str = ""
    currency: str = "INR"

    @property
    def recommended_amount(self) -> Decimal:
        return self.suggested_amount

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adjustment_id": self.adjustment_id,
            "invoice_id": self.invoice_id,
            "adjustment_type": self.adjustment_type,
            "suggested_amount": float(self.suggested_amount),
            "reason": self.reason,
            "counterparty_id": self.counterparty_id,
            "reference_rule": self.reference_rule,
            "action_owner": self.action_owner,
            "statutory_provision": self.statutory_provision,
            "currency": self.currency,
        }
