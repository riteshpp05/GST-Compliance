"""
UC15 GST Compliance Agent — Central Rule Registry (v2.0)
Manages rule lifecycle, registration, lookup, category filtering, and dynamic rule toggling.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from app.domain.enums.rule_category import RuleCategory
from app.rules.base import ComplianceRule
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RuleRegistry:
    """Central registry holding active compliance and data quality rules."""

    def __init__(self):
        self._rules: Dict[str, ComplianceRule] = {}
        self._enabled_overrides: Dict[str, bool] = {}

    def register(self, rule: ComplianceRule) -> None:
        """Register a compliance rule."""
        if rule.rule_id in self._rules:
            logger.warning(f"Overwriting existing rule registration for {rule.rule_id}")
        self._rules[rule.rule_id] = rule
        logger.debug(f"Registered rule: {rule.rule_id} ({rule.name}) v{rule.version}")

    def get(self, rule_id: str) -> Optional[ComplianceRule]:
        """Retrieve a rule by its rule_id."""
        return self._rules.get(rule_id)

    def all(self) -> List[ComplianceRule]:
        """Return all registered rules."""
        return list(self._rules.values())

    @property
    def rules(self) -> List[ComplianceRule]:
        """Return all registered rules (convenience property)."""
        return self.all()

    def is_enabled(self, rule: ComplianceRule) -> bool:
        """Check if rule is active, accounting for dynamic overrides."""
        if rule.rule_id in self._enabled_overrides:
            return self._enabled_overrides[rule.rule_id]
        return rule.enabled

    def enabled(self) -> List[ComplianceRule]:
        """Return all active rules."""
        return [r for r in self._rules.values() if self.is_enabled(r)]

    def enable(self, rule_id: str) -> bool:
        """Dynamically enable a rule by ID."""
        if rule_id in self._rules:
            self._enabled_overrides[rule_id] = True
            logger.info(f"Enabled rule: {rule_id}")
            return True
        logger.warning(f"Cannot enable unregistered rule: {rule_id}")
        return False

    def disable(self, rule_id: str) -> bool:
        """Dynamically disable a rule by ID."""
        if rule_id in self._rules:
            self._enabled_overrides[rule_id] = False
            logger.info(f"Disabled rule: {rule_id}")
            return True
        logger.warning(f"Cannot disable unregistered rule: {rule_id}")
        return False

    def by_category(self, category: RuleCategory) -> List[ComplianceRule]:
        """Filter registered rules by category."""
        return [r for r in self._rules.values() if r.category == category]

    def clear(self) -> None:
        """Clear all registered rules and overrides."""
        self._rules.clear()
        self._enabled_overrides.clear()

    def __len__(self) -> int:
        return len(self._rules)


def create_default_registry(include_data_quality: bool = False, include_extended: bool = False) -> RuleRegistry:
    """
    Factory creating a registry pre-populated with statutory 6 rules,
    and optionally extended rules and data quality rules.
    """
    from app.rules.existing.gstin import GSTINFormatRule
    from app.rules.existing.hsn import HSNValidityRule
    from app.rules.existing.tax import TaxRateCorrectnessRule
    from app.rules.existing.pos import PlaceOfSupplyRule
    from app.rules.existing.eway import EWayBillComplianceRule
    from app.rules.existing.itc import ITCEligibilityRule

    registry = RuleRegistry()
    # 1. Statutory 6 Gates
    registry.register(GSTINFormatRule())
    registry.register(HSNValidityRule())
    registry.register(TaxRateCorrectnessRule())
    registry.register(PlaceOfSupplyRule())
    registry.register(EWayBillComplianceRule())
    registry.register(ITCEligibilityRule())

    if include_extended:
        from app.rules.existing.rcm import ReverseChargeRule
        from app.rules.existing.cdn import CreditDebitNoteRule
        from app.rules.existing.itc_180 import ITC180DayPaymentRule
        registry.register(ReverseChargeRule())
        registry.register(CreditDebitNoteRule())
        registry.register(ITC180DayPaymentRule())

    # 2. Optional Data Quality Pre-check Rules (DATA_001 to DATA_005)
    if include_data_quality:
        from app.rules.data_quality import (
            CounterpartyInfoRule,
            MandatoryInvoiceIdRule,
            NonNegativeTaxableValueRule,
            NumericTaxRateRule,
            ValidInvoiceDateRule,
        )
        registry.register(MandatoryInvoiceIdRule())
        registry.register(ValidInvoiceDateRule())
        registry.register(NonNegativeTaxableValueRule())
        registry.register(NumericTaxRateRule())
        registry.register(CounterpartyInfoRule())

    return registry


def create_enterprise_registry(include_data_quality: bool = True) -> RuleRegistry:
    """
    Factory creating a comprehensive Enterprise Rule Registry populated with all statutory controls.
    """
    return create_default_registry(include_data_quality=include_data_quality, include_extended=True)

