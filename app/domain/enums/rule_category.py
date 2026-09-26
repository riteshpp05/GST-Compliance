"""
UC15 GST Compliance Agent — Rule Category Enum
"""
from __future__ import annotations
from enum import Enum


class RuleCategory(str, Enum):
    """
    Categorization of GST compliance and audit rules.
    """
    MASTER_DATA = "MASTER_DATA"
    CLASSIFICATION = "CLASSIFICATION"
    TAX = "TAX"
    PLACE_OF_SUPPLY = "PLACE_OF_SUPPLY"
    EWAY_BILL = "EWAY_BILL"
    E_INVOICE = "E_INVOICE"
    ITC = "ITC"
    RCM = "RCM"
    CREDIT_DEBIT_NOTE = "CREDIT_DEBIT_NOTE"
    PAYMENT_180_DAYS = "PAYMENT_180_DAYS"
    RECONCILIATION = "RECONCILIATION"
    SAP_TAX_CODE = "SAP_TAX_CODE"
    DATA_QUALITY = "DATA_QUALITY"
    OTHER = "OTHER"

    @classmethod
    def from_str(cls, value: str) -> "RuleCategory":
        normalized = value.strip().upper()
        if normalized in ("TAX_RATES", "TAX_RATE"):
            return cls.TAX
        if normalized in ("ITC_ELIGIBILITY", "ITC_POLICY"):
            return cls.ITC
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unknown RuleCategory: {value}")

# Class-level aliases for backward compatibility with existing rules
RuleCategory.TAX_RATES = RuleCategory.TAX  # type: ignore
RuleCategory.ITC_ELIGIBILITY = RuleCategory.ITC  # type: ignore

