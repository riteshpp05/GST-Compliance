"""
UC15 GST Compliance Agent — Exception Management Models (Phase 7)
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExceptionCategory(str, Enum):
    TAX_EXCEPTIONS = "TAX_EXCEPTIONS"
    EWAY_EXCEPTIONS = "EWAY_EXCEPTIONS"
    EINVOICE_EXCEPTIONS = "EINVOICE_EXCEPTIONS"
    ITC_EXCEPTIONS = "ITC_EXCEPTIONS"
    RCM_EXCEPTIONS = "RCM_EXCEPTIONS"
    SAP_MAPPING_EXCEPTIONS = "SAP_MAPPING_EXCEPTIONS"
    DATA_QUALITY_EXCEPTIONS = "DATA_QUALITY_EXCEPTIONS"


class ExceptionStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class FinanceException(BaseModel):
    """Business-level exception grouping one or more raw rule failures."""
    exception_id: str
    transaction_id: str
    document_number: str
    category: ExceptionCategory
    issue_title: str
    severity: str = "HIGH"
    status: ExceptionStatus = ExceptionStatus.OPEN
    root_cause: str
    actual_value: Any
    expected_value: Any
    evidence: Dict[str, Any] = Field(default_factory=dict)
    financial_exposure: float = 0.0
    recommended_action: str
    owner: str = "Finance Team"
