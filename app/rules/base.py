"""
UC15 GST Compliance Agent — Compliance Rule Base Interface (v2.0)
Defines the formal contract for all GST compliance and data-quality rules.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.rules.context import ValidationContext


class ComplianceRule(ABC):
    """
    Abstract base interface for all GST compliance and data quality rules.
    Rules are versioned, categorized, toggleable, and return standard ValidationResult contracts.
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique rule identifier (e.g., GSTIN_001, DATA_001)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the rule."""

    @property
    @abstractmethod
    def category(self) -> RuleCategory:
        """Functional domain category of the rule."""

    @property
    def severity(self) -> Severity:
        """Default severity if this rule fails."""
        return Severity.MEDIUM

    @property
    def version(self) -> str:
        """Semantic version of the rule logic."""
        return "2.0"

    @property
    def gate_no(self) -> Optional[int]:
        """Optional sequential gate number for 6-gate statutory architecture."""
        return None

    @property
    def description(self) -> str:
        """Statutory reference or architectural explanation."""
        return self.__doc__ or self.name

    @property
    def enabled(self) -> bool:
        """Whether this rule is active."""
        return True

    @abstractmethod
    def validate(
        self,
        invoice: Invoice,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        """
        Validate the invoice against this compliance rule.
        Returns a strongly-typed, evidence-backed ValidationResult contract.
        """
