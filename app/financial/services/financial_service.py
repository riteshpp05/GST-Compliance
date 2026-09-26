"""
app.financial.services.financial_service
========================================
High-level service orchestrating financial impact calculations, persistence,
aggregations, trend analysis, adjustment generation, and reporting.
"""

from typing import Dict, List, Optional, Union
from decimal import Decimal

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision as Decision
from app.financial.models.impact import (
    FinancialImpact,
    FinancialImpactType,
    ImpactDirection,
    CalculationStatus,
)
from app.financial.models.exposure import (
    CounterpartyFinancialExposure,
    RuleFinancialExposure,
    PeriodFinancialExposure,
    PeriodExposureTrend,
)
from app.financial.models.adjustment import FinancialAdjustment
from app.financial.models.aggregate import AggregateFinancialExposure
from app.financial.models.report import FinancialReport
from app.financial.calculators.exposure_calculator import InvoiceExposureCalculator
from app.financial.calculators.aggregate_calculator import AggregateCalculator
from app.financial.repositories.base import BaseFinancialRepository
from app.financial.repositories.in_memory import InMemoryFinancialRepository


class FinancialService:
    """
    Central service for deterministic GST financial impact analysis,
    exposure aggregation, and financial reporting.
    """

    def __init__(
        self,
        repository: Optional[BaseFinancialRepository] = None,
        exposure_calculator: Optional[InvoiceExposureCalculator] = None,
        aggregate_calculator: Optional[AggregateCalculator] = None,
    ) -> None:
        self.repository = repository or InMemoryFinancialRepository()
        self.exposure_calculator = exposure_calculator or InvoiceExposureCalculator()
        self.aggregate_calculator = aggregate_calculator or AggregateCalculator()

    def evaluate_decision(
        self, decision: Decision, invoice: Optional[Invoice] = None
    ) -> List[FinancialImpact]:
        """
        Evaluate the financial impact for a single compliance Decision.
        Stores the resulting FinancialImpacts in the repository and returns them.
        """
        impacts = self.exposure_calculator.calculate_invoice_impact(decision, invoice)
        self.repository.add_batch(impacts)
        return impacts

    def evaluate_batch(
        self,
        decisions: List[Decision],
        invoices: Optional[Union[List[Invoice], Dict[str, Invoice]]] = None,
    ) -> List[FinancialImpact]:
        """
        Evaluate financial impacts for a batch of Decisions.
        Accepts invoices either as a list or as a mapping keyed by invoice_id.
        Stores all results in the repository and returns them.
        """
        inv_map: Dict[str, Invoice] = {}
        if invoices:
            if isinstance(invoices, dict):
                inv_map = invoices
            else:
                inv_map = {inv.invoice_id: inv for inv in invoices}

        impacts: List[FinancialImpact] = []
        for d in decisions:
            inv_id = getattr(d, "invoice_id", None) or getattr(d, "invoice_no", None)
            inv = inv_map.get(inv_id) if inv_id else None
            imps = self.exposure_calculator.calculate_invoice_impact(d, inv)
            impacts.extend(imps)

        self.repository.add_batch(impacts)
        return impacts

    def get_impact_by_invoice_id(self, invoice_id: str) -> Optional[FinancialImpact]:
        """Retrieve stored financial impact for a specific invoice."""
        return self.repository.get_by_invoice_id(invoice_id)

    def list_all_impacts(self) -> List[FinancialImpact]:
        """Retrieve all stored financial impact records."""
        return self.repository.list_all()

    def get_aggregate_exposure(self) -> AggregateFinancialExposure:
        """Calculate and return portfolio-level aggregate exposure from all stored impacts."""
        all_impacts = self.repository.list_all()
        return self.aggregate_calculator.aggregate_portfolio(all_impacts)

    def get_top_exposures(self, n: int = 5) -> List[FinancialImpact]:
        """Return the top N financial exposures, ranked deterministically."""
        all_impacts = self.repository.list_all()
        return self.aggregate_calculator.get_top_exposures(all_impacts, n=n)

    def get_counterparty_exposures(
        self, counterparty_id: Optional[str] = None
    ) -> List[CounterpartyFinancialExposure]:
        """
        Aggregate exposure by counterparty across all stored impacts.
        If counterparty_id is provided, returns exposures only for that counterparty.
        """
        if counterparty_id:
            impacts = self.repository.query_by_counterparty(counterparty_id)
        else:
            impacts = self.repository.list_all()
        return self.aggregate_calculator.aggregate_by_counterparty(impacts)

    def get_counterparty_exposure(
        self, counterparty_id: str
    ) -> Optional[CounterpartyFinancialExposure]:
        """Retrieve exposure summary for a specific counterparty, or None if no impacts exist."""
        exposures = self.get_counterparty_exposures(counterparty_id)
        return exposures[0] if exposures else None

    def get_rule_exposures(self, rule_id: Optional[str] = None) -> List[RuleFinancialExposure]:
        """
        Aggregate exposure by rule ID across all stored impacts.
        If rule_id is provided, returns exposures only for that rule.
        """
        if rule_id:
            impacts = self.repository.query_by_rule(rule_id)
        else:
            impacts = self.repository.list_all()
        return self.aggregate_calculator.aggregate_by_rule(impacts)

    def get_rule_exposure(self, rule_id: str) -> Optional[RuleFinancialExposure]:
        """Retrieve exposure summary for a specific rule ID, or None if no impacts exist."""
        exposures = self.get_rule_exposures(rule_id)
        return exposures[0] if exposures else None

    def get_period_exposures(self) -> List[PeriodFinancialExposure]:
        """Aggregate exposure grouped by filing period (YYYY-MM)."""
        all_impacts = self.repository.list_all()
        return self.aggregate_calculator.aggregate_by_period(all_impacts)

    def get_period_trends(self) -> List[PeriodExposureTrend]:
        """Compute month-over-month exposure delta trends."""
        period_exposures = self.get_period_exposures()
        return self.aggregate_calculator.compute_period_trends(period_exposures)

    def generate_adjustments(self) -> List[FinancialAdjustment]:
        """
        Generate deterministic adjustment recommendations for all qualifying impacts.
        """
        adjustments: List[FinancialAdjustment] = []
        all_impacts = self.repository.list_all()

        for impact in all_impacts:
            if (
                impact.calculation_status != CalculationStatus.CALCULATED
                or impact.potential_exposure is None
                or impact.potential_exposure <= Decimal("0.00")
            ):
                continue

            if impact.impact_type == FinancialImpactType.TAX_RATE_DIFFERENCE:
                if impact.direction == ImpactDirection.OVERCHARGED_TAX:
                    adjustments.append(
                        FinancialAdjustment(
                            adjustment_id=f"ADJ-{impact.invoice_id}-{impact.rule_id}",
                            invoice_id=impact.invoice_id,
                            counterparty_id=impact.counterparty_id,
                            adjustment_type="CREDIT_NOTE_REQUIRED",
                            suggested_amount=impact.potential_exposure,
                            reason=(
                                f"Tax was overcharged by {impact.rate_difference_pct}%. "
                                f"Request supplier to issue a Credit Note under Section 34(1) for INR {impact.potential_exposure}."
                            ),
                            reference_rule=impact.rule_id,
                            action_owner="VENDOR",
                            statutory_provision="Section 34(1) CGST Act, 2017",
                        )
                    )
                elif impact.direction == ImpactDirection.UNDERCHARGED_TAX:
                    adjustments.append(
                        FinancialAdjustment(
                            adjustment_id=f"ADJ-{impact.invoice_id}-{impact.rule_id}",
                            invoice_id=impact.invoice_id,
                            counterparty_id=impact.counterparty_id,
                            adjustment_type="DEBIT_NOTE_REQUIRED",
                            suggested_amount=impact.potential_exposure,
                            reason=(
                                f"Tax was undercharged by {abs(impact.rate_difference_pct)}%. "
                                f"Supplier should issue a Debit Note under Section 34(3) for INR {impact.potential_exposure}."
                            ),
                            reference_rule=impact.rule_id,
                            action_owner="VENDOR",
                            statutory_provision="Section 34(3) CGST Act, 2017",
                        )
                    )

            elif impact.impact_type == FinancialImpactType.ITC_EXPOSURE:
                adjustments.append(
                    FinancialAdjustment(
                        adjustment_id=f"ADJ-{impact.invoice_id}-{impact.rule_id}",
                        invoice_id=impact.invoice_id,
                        counterparty_id=impact.counterparty_id,
                        adjustment_type="ITC_REVERSAL_REQUIRED",
                        suggested_amount=impact.potential_exposure,
                        reason=(
                            f"ITC claimed on blocked category under Section 17(5). "
                            f"Reverse ITC of INR {impact.potential_exposure} in Table 4(B) of GSTR-3B."
                        ),
                        reference_rule=impact.rule_id,
                        action_owner="TAXPAYER",
                        statutory_provision="Section 17(5) CGST Act, 2017",
                    )
                )

        return adjustments

    def generate_report(self, top_n: int = 5) -> FinancialReport:
        """
        Generate a comprehensive FinancialReport compiling portfolio aggregate,
        top exposures, counterparty/rule/period breakdowns, trends, and adjustments.
        """
        all_impacts = self.repository.list_all()
        aggregate = self.aggregate_calculator.aggregate_portfolio(all_impacts)
        top_exposures = self.aggregate_calculator.get_top_exposures(all_impacts, n=top_n)
        counterparty_exposures = self.aggregate_calculator.aggregate_by_counterparty(all_impacts)
        rule_exposures = self.aggregate_calculator.aggregate_by_rule(all_impacts)
        period_exposures = self.aggregate_calculator.aggregate_by_period(all_impacts)
        period_trends = self.aggregate_calculator.compute_period_trends(period_exposures)
        adjustments = self.generate_adjustments()

        return FinancialReport(
            aggregate=aggregate,
            top_exposures=top_exposures,
            counterparty_exposures=counterparty_exposures,
            rule_exposures=rule_exposures,
            period_exposures=period_exposures,
            period_trends=period_trends,
            adjustments=adjustments,
        )

    def clear(self) -> None:
        """Clear all stored data in the repository."""
        self.repository.clear()
