"""
UC15 GST Compliance Agent — Validation Engine
Executes compliance rules against canonical invoices and produces structured ValidationReports.
"""
from __future__ import annotations

from typing import List, Optional, Union
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationReport, ValidationResult
from app.infrastructure.logging import get_logger
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext
from app.rules.registry import RuleRegistry, create_default_registry

logger = get_logger(__name__)


class ValidationEngine:
    """
    Core validation engine responsible for sequential/parallel rule execution.
    Pure validator: does not make compliance decisions, calculate risk, or mutate data.
    """

    def __init__(
        self,
        registry_or_rules: Optional[Union[RuleRegistry, List[ComplianceRule]]] = None,
        context: Optional[ValidationContext] = None,
    ):
        if registry_or_rules is None:
            self.registry = create_default_registry()
            self._rules = self.registry.enabled()
        elif isinstance(registry_or_rules, RuleRegistry):
            self.registry = registry_or_rules
            self._rules = self.registry.enabled()
        else:
            self._rules = list(registry_or_rules)
            self.registry = RuleRegistry()
            for r in self._rules:
                self.registry.register(r)

        self.context = context or ValidationContext()

    def validate(self, invoice: Invoice) -> ValidationReport:
        """
        Execute enabled compliance rules against a single invoice.
        Returns a ValidationReport.
        """
        logger.debug(f"Validating invoice: {invoice.invoice_number}")
        results: List[ValidationResult] = []

        # Sprint 4: Initialize reference snapshot for invoice audit trail
        snapshot = None
        if getattr(self.context, "reference_service", None):
            from datetime import date, datetime
            inv_date = invoice.invoice_date
            target_date = date(2023, 1, 1)
            if isinstance(inv_date, date):
                target_date = inv_date
            elif isinstance(inv_date, str):
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        target_date = datetime.strptime(inv_date.strip(), fmt).date()
                        break
                    except ValueError:
                        continue
            snapshot = self.context.reference_service.create_snapshot(
                invoice_id=invoice.invoice_number,
                transaction_date=target_date,
            )
            self.context.current_snapshot = snapshot

        for rule in self._rules:
            try:
                res = rule.validate(invoice, context=self.context)
                results.append(res)
            except Exception as e:
                logger.error(f"Rule {rule.rule_id} failed with error: {e}", exc_info=True)
                from app.domain.enums.validation_status import ValidationStatus
                from app.domain.enums.severity import Severity
                err_result = ValidationResult(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    gate_no=rule.gate_no,
                    status=ValidationStatus.ERROR,
                    severity=Severity.CRITICAL,
                    category=rule.category,
                    message=f"Rule execution error: {str(e)}",
                    actual_value=None,
                    expected_value=None,
                )
                results.append(err_result)

        report_meta = {}
        if snapshot:
            snapshot.freeze()
            report_meta["reference_snapshot"] = snapshot.to_dict()

        report = ValidationReport(
            invoice_id=invoice.invoice_number,
            results=results,
            metadata=report_meta,
        )
        return report

    def validate_batch(self, invoices: List[Invoice]) -> List[ValidationReport]:
        """Validate a batch of invoices."""
        return [self.validate(inv) for inv in invoices]
