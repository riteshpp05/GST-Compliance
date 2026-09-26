"""
UC15 GST Compliance Agent — Aggregate Financial Calculator (Sprint 6)
Aggregates invoice-level financial impacts into multi-dimensional summaries
across counterparties, statutory rules, and chronological time periods.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.financial.models.aggregate import AggregateFinancialExposure
from app.financial.models.exposure import (
    CounterpartyFinancialExposure,
    PeriodExposureTrend,
    PeriodFinancialExposure,
    RuleFinancialExposure,
)
from app.financial.models.impact import CalculationStatus, FinancialImpact, FinancialImpactType, ImpactDirection, round_monetary
from app.historical.analyzers.period_analyzer import PeriodAnalyzer
from app.historical.models.period import PeriodType


class AggregateCalculator:
    """
    Computes portfolio-wide and multi-dimensional financial exposure aggregates.
    Strictly excludes UNDETERMINED impacts from monetary totals.
    """

    def aggregate(self, impacts: List[FinancialImpact]) -> AggregateFinancialExposure:
        """
        Aggregate all financial impacts into a global AggregateFinancialExposure summary.
        """
        agg = AggregateFinancialExposure()
        if not impacts:
            return agg

        invoices_seen = set()
        impacted_invoices = set()
        clean_invoices = set()
        counterparties_seen = set()
        rules_seen = set()
        periods_seen = set()

        by_rule: Dict[str, Decimal] = defaultdict(Decimal)
        by_counterparty: Dict[str, Decimal] = defaultdict(Decimal)
        by_period: Dict[str, Decimal] = defaultdict(Decimal)

        for imp in impacts:
            invoices_seen.add(imp.invoice_id)
            if imp.counterparty_id:
                counterparties_seen.add(imp.counterparty_id)
            if imp.rule_id and imp.rule_id != "COMPLIANT":
                rules_seen.add(imp.rule_id)

            pkey = PeriodAnalyzer.get_period_key(imp.invoice_date, PeriodType.MONTHLY)
            periods_seen.add(pkey)

            # Calculation status tracking
            status = imp.calculation_status
            if status == CalculationStatus.CALCULATED:
                agg.calculated_count += 1
            elif status == CalculationStatus.PARTIALLY_CALCULATED:
                agg.partially_calculated_count += 1
            elif status == CalculationStatus.UNDETERMINED:
                agg.undetermined_count += 1
            elif status == CalculationStatus.NOT_APPLICABLE:
                agg.not_applicable_count += 1

            # Determine if this invoice has quantifiable impact
            exp = imp.potential_exposure
            has_quantified_exp = (
                status in (CalculationStatus.CALCULATED, CalculationStatus.PARTIALLY_CALCULATED)
                and exp is not None
                and exp > Decimal("0.00")
            )

            if has_quantified_exp:
                impacted_invoices.add(imp.invoice_id)
                agg.total_potential_exposure += exp

                # Add to rule, counterparty, and period breakdowns
                if imp.rule_id:
                    by_rule[imp.rule_id] += exp
                if imp.counterparty_id:
                    by_counterparty[imp.counterparty_id] += exp
                by_period[pkey] += exp

                # Type-specific sums
                if imp.impact_type == FinancialImpactType.TAX_RATE_DIFFERENCE:
                    agg.total_tax_difference += exp
                elif imp.impact_type == FinancialImpactType.ITC_EXPOSURE:
                    agg.total_itc_exposure += exp

                # Directional sums
                if imp.direction == ImpactDirection.OVERCHARGED_TAX:
                    agg.overcharged_tax_total += exp
                elif imp.direction == ImpactDirection.UNDERCHARGED_TAX:
                    agg.undercharged_tax_total += exp
            else:
                if status == CalculationStatus.NOT_APPLICABLE:
                    clean_invoices.add(imp.invoice_id)

        agg.total_invoices_analyzed = len(invoices_seen)
        agg.impacted_invoices_count = len(impacted_invoices)
        agg.clean_invoices_count = len(invoices_seen - impacted_invoices)

        agg.by_rule = dict(by_rule)
        agg.by_counterparty = dict(by_counterparty)
        agg.by_period = dict(by_period)

        agg.affected_invoices = sorted(list(impacted_invoices))
        agg.affected_counterparties = sorted(list(counterparties_seen))
        agg.rule_ids = sorted(list(rules_seen))
        agg.periods = sorted(list(periods_seen))

        return agg

    def build_counterparty_exposures(
        self,
        impacts: List[FinancialImpact],
    ) -> List[CounterpartyFinancialExposure]:
        """
        Aggregate financial exposure per counterparty.
        """
        cp_impacts: Dict[str, List[FinancialImpact]] = defaultdict(list)
        for imp in impacts:
            cid = imp.counterparty_id or imp.counterparty_name or "UNKNOWN"
            cp_impacts[cid].append(imp)

        profiles: List[CounterpartyFinancialExposure] = []
        for cid, group in sorted(cp_impacts.items()):
            cname = group[0].counterparty_name or cid
            direction = group[0].evidence.get("direction", "AR") if group[0].evidence else "AR"

            inv_ids = set()
            impacted_inv_ids = set()
            rule_exposures: Dict[str, Decimal] = defaultdict(Decimal)

            total_exp = Decimal("0.00")
            tax_diff_exp = Decimal("0.00")
            itc_exp = Decimal("0.00")
            overcharged_exp = Decimal("0.00")
            undercharged_exp = Decimal("0.00")
            undetermined_cnt = 0

            for imp in group:
                inv_ids.add(imp.invoice_id)
                exp = imp.potential_exposure

                if imp.calculation_status == CalculationStatus.UNDETERMINED:
                    undetermined_cnt += 1

                if (
                    imp.calculation_status in (CalculationStatus.CALCULATED, CalculationStatus.PARTIALLY_CALCULATED)
                    and exp is not None
                    and exp > Decimal("0.00")
                ):
                    impacted_inv_ids.add(imp.invoice_id)
                    total_exp += exp
                    rule_exposures[imp.rule_id] += exp

                    if imp.impact_type == FinancialImpactType.TAX_RATE_DIFFERENCE:
                        tax_diff_exp += exp
                    elif imp.impact_type == FinancialImpactType.ITC_EXPOSURE:
                        itc_exp += exp

                    if imp.direction == ImpactDirection.OVERCHARGED_TAX:
                        overcharged_exp += exp
                    elif imp.direction == ImpactDirection.UNDERCHARGED_TAX:
                        undercharged_exp += exp

            top_rules = sorted(rule_exposures.items(), key=lambda x: x[1], reverse=True)

            profiles.append(
                CounterpartyFinancialExposure(
                    counterparty_id=cid,
                    counterparty_name=cname,
                    direction=direction,
                    invoice_count=len(inv_ids),
                    impacted_invoice_count=len(impacted_inv_ids),
                    total_potential_exposure=total_exp,
                    tax_difference_exposure=tax_diff_exp,
                    itc_exposure=itc_exp,
                    overcharged_tax_total=overcharged_exp,
                    undercharged_tax_total=undercharged_exp,
                    undetermined_count=undetermined_cnt,
                    top_exposure_rules=top_rules,
                    affected_invoices=sorted(list(impacted_inv_ids)),
                )
            )

        # Sort by total_potential_exposure DESC, tie-break by counterparty_id ASC
        return sorted(profiles, key=lambda p: (-p.total_potential_exposure, p.counterparty_id))

    def build_rule_exposures(
        self,
        impacts: List[FinancialImpact],
    ) -> List[RuleFinancialExposure]:
        """
        Aggregate financial exposure per statutory rule.
        """
        rule_map: Dict[str, List[FinancialImpact]] = defaultdict(list)
        for imp in impacts:
            if imp.rule_id and imp.rule_id != "COMPLIANT":
                rule_map[imp.rule_id].append(imp)

        rule_exposures: List[RuleFinancialExposure] = []
        for rid, group in sorted(rule_map.items()):
            rcat = group[0].rule_category or "STATUTORY"
            inv_ids = set()
            total_exp = Decimal("0.00")
            status_counts: Dict[str, int] = defaultdict(int)

            for imp in group:
                status_counts[imp.calculation_status.value] += 1
                exp = imp.potential_exposure
                if (
                    imp.calculation_status in (CalculationStatus.CALCULATED, CalculationStatus.PARTIALLY_CALCULATED)
                    and exp is not None
                    and exp > Decimal("0.00")
                ):
                    inv_ids.add(imp.invoice_id)
                    total_exp += exp

            rule_exposures.append(
                RuleFinancialExposure(
                    rule_id=rid,
                    rule_category=rcat,
                    affected_invoice_count=len(inv_ids),
                    total_potential_exposure=total_exp,
                    calculation_status_counts=dict(status_counts),
                    affected_invoices=sorted(list(inv_ids)),
                )
            )

        # Sort by total_potential_exposure DESC, tie-break by rule_id ASC
        return sorted(rule_exposures, key=lambda r: (-r.total_potential_exposure, r.rule_id))

    def build_period_exposures(
        self,
        impacts: List[FinancialImpact],
        period_type: PeriodType = PeriodType.MONTHLY,
    ) -> List[PeriodFinancialExposure]:
        """
        Aggregate financial exposure over chronological time periods.
        """
        period_map: Dict[str, List[FinancialImpact]] = defaultdict(list)
        for imp in impacts:
            pkey = PeriodAnalyzer.get_period_key(imp.invoice_date, period_type)
            period_map[pkey].append(imp)

        period_exposures: List[PeriodFinancialExposure] = []
        for pkey in sorted(period_map.keys()):
            group = period_map[pkey]
            inv_ids = set()
            impacted_inv_ids = set()

            total_exp = Decimal("0.00")
            tax_diff_exp = Decimal("0.00")
            itc_exp = Decimal("0.00")
            overcharged_exp = Decimal("0.00")
            undercharged_exp = Decimal("0.00")
            undetermined_cnt = 0

            for imp in group:
                inv_ids.add(imp.invoice_id)
                exp = imp.potential_exposure

                if imp.calculation_status == CalculationStatus.UNDETERMINED:
                    undetermined_cnt += 1

                if (
                    imp.calculation_status in (CalculationStatus.CALCULATED, CalculationStatus.PARTIALLY_CALCULATED)
                    and exp is not None
                    and exp > Decimal("0.00")
                ):
                    impacted_inv_ids.add(imp.invoice_id)
                    total_exp += exp

                    if imp.impact_type == FinancialImpactType.TAX_RATE_DIFFERENCE:
                        tax_diff_exp += exp
                    elif imp.impact_type == FinancialImpactType.ITC_EXPOSURE:
                        itc_exp += exp

                    if imp.direction == ImpactDirection.OVERCHARGED_TAX:
                        overcharged_exp += exp
                    elif imp.direction == ImpactDirection.UNDERCHARGED_TAX:
                        undercharged_exp += exp

            period_exposures.append(
                PeriodFinancialExposure(
                    period_key=pkey,
                    period_type=period_type.value,
                    invoice_count=len(inv_ids),
                    impacted_invoice_count=len(impacted_inv_ids),
                    total_potential_exposure=total_exp,
                    tax_difference_exposure=tax_diff_exp,
                    itc_exposure=itc_exp,
                    overcharged_tax_total=overcharged_exp,
                    undercharged_tax_total=undercharged_exp,
                    undetermined_count=undetermined_cnt,
                    affected_invoices=sorted(list(impacted_inv_ids)),
                )
            )

        return period_exposures

    def build_period_trends(
        self,
        period_exposures: List[PeriodFinancialExposure],
    ) -> List[PeriodExposureTrend]:
        """
        Compute sequential period-over-period exposure trajectories.
        """
        trends: List[PeriodExposureTrend] = []
        for i, curr in enumerate(period_exposures):
            if i == 0:
                trends.append(
                    PeriodExposureTrend(
                        current_period=curr.period_key,
                        previous_period=None,
                        current_exposure=curr.total_potential_exposure,
                        previous_exposure=None,
                        absolute_change=None,
                        percentage_change=None,
                        direction="INSUFFICIENT_DATA",
                        description=f"Baseline period {curr.period_key}: Exposure of INR {curr.total_potential_exposure:,.2f}.",
                    )
                )
                continue

            prev = period_exposures[i - 1]
            abs_change = curr.total_potential_exposure - prev.total_potential_exposure
            pct_change = None
            if prev.total_potential_exposure > Decimal("0.00"):
                pct_change = float(
                    round_monetary(((abs_change / prev.total_potential_exposure) * Decimal("100.00")))
                )

            # Determine direction: +/- 5% threshold
            if pct_change is None:
                direction = "INSUFFICIENT_DATA"
                desc = f"Exposure in {curr.period_key} was INR {curr.total_potential_exposure:,.2f} (baseline was zero)."
            elif pct_change >= 5.0:
                direction = "INCREASING"
                desc = f"Exposure increased by {pct_change:+.1f}% from {prev.period_key} (INR {prev.total_potential_exposure:,.2f}) to {curr.period_key} (INR {curr.total_potential_exposure:,.2f})."
            elif pct_change <= -5.0:
                direction = "DECREASING"
                desc = f"Exposure decreased by {pct_change:.1f}% from {prev.period_key} (INR {prev.total_potential_exposure:,.2f}) to {curr.period_key} (INR {curr.total_potential_exposure:,.2f})."
            else:
                direction = "STABLE"
                desc = f"Exposure remained stable in {curr.period_key} (change: {pct_change:+.1f}%)."

            trends.append(
                PeriodExposureTrend(
                    current_period=curr.period_key,
                    previous_period=prev.period_key,
                    current_exposure=curr.total_potential_exposure,
                    previous_exposure=prev.total_potential_exposure,
                    absolute_change=abs_change,
                    percentage_change=pct_change,
                    direction=direction,
                    description=desc,
                )
            )

        return trends

    def get_top_exposures(
        self,
        impacts: List[FinancialImpact],
        limit: int = 10,
        n: Optional[int] = None,
    ) -> List[FinancialImpact]:
        """
        Deterministic ranking of top potential exposures.
        Sorted by potential_exposure DESC, invoice_date, invoice_id.
        """
        effective_limit = n if n is not None else limit
        # Filter to impacts with quantified potential exposure > 0
        quantified = [
            imp for imp in impacts
            if imp.calculation_status in (CalculationStatus.CALCULATED, CalculationStatus.PARTIALLY_CALCULATED)
            and imp.potential_exposure is not None
            and imp.potential_exposure > Decimal("0.00")
        ]

        # Primary sort: potential_exposure DESC
        # Secondary tie-break: invoice_date (descending)
        # Tertiary tie-break: invoice_id (ascending)
        # Quaternary tie-break: rule_id (ascending)
        def sort_key(imp: FinancialImpact):
            d = imp.invoice_date or date(2023, 1, 1)
            return (-imp.potential_exposure, -d.toordinal(), imp.invoice_id, imp.rule_id)

        ranked = sorted(quantified, key=sort_key)
        return ranked[:effective_limit]

    # Backward/Convenience Aliases
    aggregate_portfolio = aggregate
    aggregate_by_counterparty = build_counterparty_exposures
    aggregate_by_rule = build_rule_exposures
    aggregate_by_period = build_period_exposures
    compute_period_trends = build_period_trends
