"""
Unit tests for ExceptionHub grouping.
"""
from app.domain.models.validation import ValidationResult
from app.exception.exception_hub import ExceptionHub
from app.exception.models import ExceptionCategory


def test_exception_hub_grouping():
    results = [
        ValidationResult(
            rule_id="TAX_001",
            rule_name="Tax Rate Math",
            status="FAIL",
            message="Tax rate mismatch 18% vs 28%",
            severity="CRITICAL",
        ),
        ValidationResult(
            rule_id="EWB_001",
            rule_name="E-Way Bill Threshold",
            status="FAIL",
            message="E-Way bill missing",
            severity="HIGH",
        ),
    ]

    exceptions = ExceptionHub.group_exceptions("101", "INV-101", results)
    assert len(exceptions) == 2
    assert exceptions[0].category == ExceptionCategory.TAX_EXCEPTIONS
    assert exceptions[1].category == ExceptionCategory.EWAY_EXCEPTIONS
