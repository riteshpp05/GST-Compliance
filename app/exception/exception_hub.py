"""
UC15 GST Compliance Agent — Exception Management Hub (Phase 7)
Groups raw rule failures into high-level business exception categories.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from app.domain.models.validation import ValidationResult
from app.exception.models import ExceptionCategory, ExceptionStatus, FinanceException


class ExceptionHub:
    """
    Aggregates raw compliance validation results into business exception groups.
    """

    @staticmethod
    def categorize_rule(rule_id: str) -> ExceptionCategory:
        r_upper = rule_id.upper()
        if "TAX" in r_upper:
            return ExceptionCategory.TAX_EXCEPTIONS
        if "EWAY" in r_upper or "EWB" in r_upper:
            return ExceptionCategory.EWAY_EXCEPTIONS
        if "IRN" in r_upper or "EINVOICE" in r_upper:
            return ExceptionCategory.EINVOICE_EXCEPTIONS
        if "ITC" in r_upper:
            return ExceptionCategory.ITC_EXCEPTIONS
        if "RCM" in r_upper:
            return ExceptionCategory.RCM_EXCEPTIONS
        if "DATA" in r_upper or "GSTIN" in r_upper or "HSN" in r_upper:
            return ExceptionCategory.DATA_QUALITY_EXCEPTIONS
        return ExceptionCategory.TAX_EXCEPTIONS

    @classmethod
    def group_exceptions(cls, transaction_id: str, document_number: str, validation_results: List[ValidationResult]) -> List[FinanceException]:
        exceptions: List[FinanceException] = []

        for idx, res in enumerate(validation_results):
            if res.status in ("FAIL", "NEEDS_REVIEW", "WARNING"):
                cat = cls.categorize_rule(res.rule_id)
                exp = float(res.financial_impact) if res.financial_impact else 0.0

                exc = FinanceException(
                    exception_id=f"EXC-{transaction_id}-{idx+1}",
                    transaction_id=transaction_id,
                    document_number=document_number,
                    category=cat,
                    issue_title=f"{res.rule_name} Exception",
                    severity=res.severity,
                    status=ExceptionStatus.OPEN,
                    root_cause=res.message,
                    actual_value=res.actual_value,
                    expected_value=res.expected_value,
                    evidence=res.evidence if isinstance(res.evidence, dict) else {},
                    financial_exposure=exp,
                    recommended_action=f"Review {res.rule_name} findings and verify supporting documents.",
                )
                exceptions.append(exc)

        return exceptions
