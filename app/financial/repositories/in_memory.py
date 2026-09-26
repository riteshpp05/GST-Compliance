"""
app.financial.repositories.in_memory
====================================
In-memory implementation of BaseFinancialRepository with indexed lookups.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Optional
from app.financial.models.impact import FinancialImpact, CalculationStatus
class InMemoryFinancialRepository:
    """
    In-memory store for FinancialImpact records with indexed lookups
    by invoice ID, counterparty ID, rule ID, and calculation status.
    """

    def __init__(self) -> None:
        self._records: Dict[str, FinancialImpact] = {}  # keyed by impact_id
        self._by_invoice: Dict[str, List[str]] = defaultdict(list)
        self._by_counterparty: Dict[str, List[str]] = defaultdict(list)
        self._by_rule: Dict[str, List[str]] = defaultdict(list)
        self._by_status: Dict[CalculationStatus, List[str]] = defaultdict(list)

    def add(self, impact: FinancialImpact) -> None:
        key = impact.impact_id
        if key in self._records:
            self._remove_from_indices(key)

        self._records[key] = impact

        if impact.invoice_id:
            self._by_invoice[impact.invoice_id].append(key)

        if impact.counterparty_id:
            self._by_counterparty[impact.counterparty_id].append(key)

        if impact.rule_id:
            self._by_rule[impact.rule_id].append(key)

        self._by_status[impact.calculation_status].append(key)

    def add_batch(self, impacts: List[FinancialImpact]) -> None:
        for impact in impacts:
            self.add(impact)

    def get_by_invoice_id(self, invoice_id: str) -> Optional[FinancialImpact]:
        """
        Retrieve primary financial impact for an invoice.
        Prefers calculated exposure > 0, otherwise first impact found.
        """
        keys = self._by_invoice.get(invoice_id, [])
        if not keys:
            return None
        impacts = [self._records[k] for k in keys if k in self._records]
        if not impacts:
            return None
        # Prioritize calculated with highest exposure, tie-break deterministically by impact_id
        sorted_impacts = sorted(
            impacts,
            key=lambda x: (
                1 if x.calculation_status == CalculationStatus.CALCULATED else 0,
                x.potential_exposure or Decimal("0.00"),
                x.impact_id,
            ),
            reverse=True,
        )
        return sorted_impacts[0]

    def get_all_by_invoice_id(self, invoice_id: str) -> List[FinancialImpact]:
        """Retrieve all financial impacts recorded for an invoice ID."""
        keys = self._by_invoice.get(invoice_id, [])
        return [self._records[k] for k in keys if k in self._records]

    def list_all(self) -> List[FinancialImpact]:
        return list(self._records.values())

    def query_by_counterparty(self, counterparty_id: str) -> List[FinancialImpact]:
        keys = self._by_counterparty.get(counterparty_id, [])
        return [self._records[k] for k in keys if k in self._records]

    def query_by_rule(self, rule_id: str) -> List[FinancialImpact]:
        keys = self._by_rule.get(rule_id, [])
        return [self._records[k] for k in keys if k in self._records]

    def query_by_status(self, status: CalculationStatus) -> List[FinancialImpact]:
        keys = self._by_status.get(status, [])
        return [self._records[k] for k in keys if k in self._records]

    def clear(self) -> None:
        self._records.clear()
        self._by_invoice.clear()
        self._by_counterparty.clear()
        self._by_rule.clear()
        self._by_status.clear()

    def count(self) -> int:
        return len(self._records)

    def _remove_from_indices(self, impact_id: str) -> None:
        old_impact = self._records.get(impact_id)
        if not old_impact:
            return
        if old_impact.invoice_id and old_impact.invoice_id in self._by_invoice:
            self._by_invoice[old_impact.invoice_id] = [
                k for k in self._by_invoice[old_impact.invoice_id] if k != impact_id
            ]
        if old_impact.counterparty_id and old_impact.counterparty_id in self._by_counterparty:
            self._by_counterparty[old_impact.counterparty_id] = [
                k for k in self._by_counterparty[old_impact.counterparty_id] if k != impact_id
            ]
        if old_impact.rule_id and old_impact.rule_id in self._by_rule:
            self._by_rule[old_impact.rule_id] = [
                k for k in self._by_rule[old_impact.rule_id] if k != impact_id
            ]
        if old_impact.calculation_status in self._by_status:
            self._by_status[old_impact.calculation_status] = [
                k for k in self._by_status[old_impact.calculation_status] if k != impact_id
            ]

