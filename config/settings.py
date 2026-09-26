"""
UC15 GST & Tax Compliance Validation Agent — Configuration (Backward Compatibility)
================================================================
Finance / SAP FI-Tax - India GST

This module provides backward-compatibility re-exports delegating to app.config.settings.
"""
from __future__ import annotations

from app.config.settings import (
    EXCEL_FILE,
    SHEET_NAME,
    EWAY_BILL_THRESHOLD_INR,
    ITC_BLOCKED_KEYWORDS,
    RATE_TOLERANCE_PCT,
    NEEDS_REVIEW_SLA_HOURS,
    NON_COMPLIANT_SLA_HOURS,
    BTP_APP_NAME,
    BTP_RUNTIME,
    BTP_MEMORY,
    API_PORT,
)
from app.config.defaults import (
    SEC_A_HEADER, SEC_A_START, SEC_A_END,
    SEC_B_HEADER, SEC_B_START, SEC_B_END,
    SEC_C_HEADER, SEC_C_START, SEC_C_END,
    SEC_D_HEADER, SEC_D_START, SEC_D_END,
)

__all__ = [
    "EXCEL_FILE",
    "SHEET_NAME",
    "SEC_A_HEADER", "SEC_A_START", "SEC_A_END",
    "SEC_B_HEADER", "SEC_B_START", "SEC_B_END",
    "SEC_C_HEADER", "SEC_C_START", "SEC_C_END",
    "SEC_D_HEADER", "SEC_D_START", "SEC_D_END",
    "EWAY_BILL_THRESHOLD_INR",
    "ITC_BLOCKED_KEYWORDS",
    "RATE_TOLERANCE_PCT",
    "NEEDS_REVIEW_SLA_HOURS",
    "NON_COMPLIANT_SLA_HOURS",
    "BTP_APP_NAME",
    "BTP_RUNTIME",
    "BTP_MEMORY",
    "API_PORT",
]
