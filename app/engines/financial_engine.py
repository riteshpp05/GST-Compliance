"""
UC15 GST Compliance Agent — Canonical Financial Exposure Engine (Sprint 22)
Quantifies potential financial exposure, structures formula traces, and prevents double-counting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.domain.models.invoice import Invoice
from app.financial.models.impact import (
    FinancialImpact,
    FinancialImpactType,
    CalculationStatus,
    ImpactDirection,
    round_monetary,
)


class CanonicalExposureType(str, Enum):
    """Canonical classification of financial exposure for finance investigations."""
    POTENTIAL_TAX_EXPOSURE = "POTENTIAL_TAX_EXPOSURE"
    TAX_DIFFERENCE = "TAX_DIFFERENCE"
    ITC_AT_RISK = "ITC_AT_RISK"
    POTENTIAL_INTEREST = "POTENTIAL_INTEREST"
    POTENTIAL_PENALTY = "POTENTIAL_PENALTY"
    TAX_OVERCHARGE = "TAX_OVERCHARGE"
    TAX_UNDERCHARGE = "TAX_UNDERCHARGE"


# Categorization of exposure types for double-count prevention
ADDITIVE_EXPOSURE_TYPES = {
    CanonicalExposureType.TAX_UNDERCHARGE,
    CanonicalExposureType.POTENTIAL_PENALTY,
    CanonicalExposureType.POTENTIAL_INTEREST,
    CanonicalExposureType.POTENTIAL_TAX_EXPOSURE,
}

OVERLAPPING_EXPOSURE_TYPES = {
    CanonicalExposureType.TAX_DIFFERENCE,
    CanonicalExposureType.ITC_AT_RISK,
}

INFORMATIONAL_EXPOSURE_TYPES = {
    CanonicalExposureType.TAX_OVERCHARGE,
}


@dataclass
class ExposureTrace:
    """
    Structured, explainable trace of a single financial exposure item.
    """
    exposure_type: str
    amount: Decimal
    currency: str = "INR"
    basis: str = ""
    calculation_trace: Dict[str, Any] = field(default_factory=dict)
    source_finding_id: str = ""
    confidence: float = 1.0
    status: str = "CALCULATED"
    is_additive: bool = True
    is_overlapping: bool = False
    is_informational: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exposure_type": self.exposure_type,
            "amount": float(self.amount),
            "currency": self.currency,
            "basis": self.basis,
            "calculation_trace": self.calculation_trace,
            "source_finding_id": self.source_finding_id,
            "confidence": self.confidence,
            "status": self.status,
            "is_additive": self.is_additive,
            "is_overlapping": self.is_overlapping,
            "is_informational": self.is_informational,
            "created_at": self.created_at,
        }


@dataclass
class CaseFinancialSummary:
    """
    Portfolio/Case level financial exposure aggregate with strict double-count separation.
    """
    case_id: str
    invoice_id: str
    additive_total: Decimal = Decimal("0.00")
    overlapping_total: Decimal = Decimal("0.00")
    informational_total: Decimal = Decimal("0.00")
    net_financial_exposure: Decimal = Decimal("0.00")
    currency: str = "INR"
    traces: List[ExposureTrace] = field(default_factory=list)
    by_type: Dict[str, Decimal] = field(default_factory=dict)
    summary_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "invoice_id": self.invoice_id,
            "additive_total": float(self.additive_total),
            "overlapping_total": float(self.overlapping_total),
            "informational_total": float(self.informational_total),
            "net_financial_exposure": float(self.net_financial_exposure),
            "currency": self.currency,
            "traces": [t.to_dict() for t in self.traces],
            "by_type": {k: float(v) for k, v in self.by_type.items()},
            "summary_notes": self.summary_notes,
        }


class FinancialExposureEngine:
    """
    Engine for generating structured exposure traces, step-by-step formula breakdowns,
    and double-count safe case financial summaries.
    """

    def create_tax_difference_trace(
        self,
        finding_id: str,
        taxable_value: Decimal,
        recorded_rate: Decimal,
        expected_rate: Decimal,
        recorded_tax: Decimal,
        expected_tax: Decimal,
        reference_version: str = "TAX_RATE_REF_V1",
    ) -> ExposureTrace:
        diff_amount = abs(recorded_tax - expected_tax)
        is_undercharge = recorded_tax < expected_tax
        exp_type = (
            CanonicalExposureType.TAX_UNDERCHARGE.value
            if is_undercharge
            else CanonicalExposureType.TAX_OVERCHARGE.value
        )
        is_add = is_undercharge
        is_info = not is_undercharge

        calc_trace = {
            "formula": "abs(recorded_tax - expected_tax) where tax = taxable_value * rate / 100",
            "inputs": {
                "taxable_value": float(taxable_value),
                "recorded_rate": float(recorded_rate),
                "expected_rate": float(expected_rate),
                "recorded_tax": float(recorded_tax),
                "expected_tax": float(expected_tax),
            },
            "rates": {
                "recorded": float(recorded_rate),
                "expected": float(expected_rate),
                "delta_pct": float(recorded_rate - expected_rate),
            },
            "sources": ["Invoice Line Item", "Statutory Rate Schedule"],
            "reference_version": reference_version,
            "result": float(diff_amount),
        }

        basis = (
            f"Tax rate mismatch: Recorded {recorded_rate}% vs Expected {expected_rate}%. "
            f"Difference of INR {diff_amount:,.2f} ({exp_type})."
        )

        return ExposureTrace(
            exposure_type=exp_type,
            amount=diff_amount,
            currency="INR",
            basis=basis,
            calculation_trace=calc_trace,
            source_finding_id=finding_id,
            confidence=1.0,
            status="CALCULATED",
            is_additive=is_add,
            is_overlapping=False,
            is_informational=is_info,
        )

    def create_itc_at_risk_trace(
        self,
        finding_id: str,
        blocked_tax_amount: Decimal,
        section: str = "17(5)",
        category: str = "Motor Vehicles / Personal Consumption",
    ) -> ExposureTrace:
        calc_trace = {
            "formula": "Sum of input tax (CGST + SGST + IGST + CESS) claimed on blocked category",
            "inputs": {
                "blocked_tax_amount": float(blocked_tax_amount),
                "statutory_provision": f"Section {section} CGST Act, 2017",
                "category": category,
            },
            "rates": {},
            "sources": ["Inward Invoice (AP)", "Section 17(5) Schedule"],
            "reference_version": "ITC_BLOCK_REF_2017",
            "result": float(blocked_tax_amount),
        }

        basis = (
            f"Potential blocked ITC under Section {section} ({category}): "
            f"INR {blocked_tax_amount:,.2f} claimed as input tax credit."
        )

        return ExposureTrace(
            exposure_type=CanonicalExposureType.ITC_AT_RISK.value,
            amount=blocked_tax_amount,
            currency="INR",
            basis=basis,
            calculation_trace=calc_trace,
            source_finding_id=finding_id,
            confidence=1.0,
            status="CALCULATED",
            is_additive=False,
            is_overlapping=True,
            is_informational=False,
        )

    def create_interest_exposure_trace(
        self,
        finding_id: str,
        base_tax_amount: Decimal,
        delay_days: int = 30,
        annual_rate_pct: Decimal = Decimal("18.00"),
    ) -> ExposureTrace:
        interest_amount = round_monetary(
            base_tax_amount * (annual_rate_pct / Decimal("100.00")) * (Decimal(delay_days) / Decimal("365.00"))
        )

        calc_trace = {
            "formula": "base_tax * (annual_rate / 100) * (delay_days / 365)",
            "inputs": {
                "base_tax_amount": float(base_tax_amount),
                "annual_rate_pct": float(annual_rate_pct),
                "delay_days": delay_days,
            },
            "rates": {"annual_interest_rate": float(annual_rate_pct)},
            "sources": ["Section 50(1) CGST Act, 2017"],
            "reference_version": "SEC_50_INTEREST_REF_2017",
            "result": float(interest_amount),
        }

        basis = (
            f"Statutory interest under Section 50(1) @ {annual_rate_pct}% p.a. for {delay_days} days "
            f"on tax shortfall of INR {base_tax_amount:,.2f}: INR {interest_amount:,.2f}."
        )

        return ExposureTrace(
            exposure_type=CanonicalExposureType.POTENTIAL_INTEREST.value,
            amount=interest_amount,
            currency="INR",
            basis=basis,
            calculation_trace=calc_trace,
            source_finding_id=finding_id,
            confidence=0.9,
            status="CALCULATED",
            is_additive=True,
            is_overlapping=False,
            is_informational=False,
        )

    def create_penalty_exposure_trace(
        self,
        finding_id: str,
        shortfall_tax_amount: Decimal,
        statutory_provision: str = "Section 122(1) CGST Act, 2017",
    ) -> ExposureTrace:
        # Penalty is 100% of tax undercharged or 10,000 minimum
        min_penalty = Decimal("10000.00")
        penalty_amount = max(shortfall_tax_amount, min_penalty)

        calc_trace = {
            "formula": "max(shortfall_tax, 10000.00) under Section 122(1)",
            "inputs": {
                "shortfall_tax_amount": float(shortfall_tax_amount),
                "statutory_minimum": float(min_penalty),
                "statutory_provision": statutory_provision,
            },
            "rates": {"penalty_pct": 100.0},
            "sources": [statutory_provision],
            "reference_version": "SEC_122_PENALTY_REF_2017",
            "result": float(penalty_amount),
        }

        basis = (
            f"Potential statutory penalty under {statutory_provision}: "
            f"INR {penalty_amount:,.2f} (100% of tax shortfall or statutory minimum INR 10,000)."
        )

        return ExposureTrace(
            exposure_type=CanonicalExposureType.POTENTIAL_PENALTY.value,
            amount=penalty_amount,
            currency="INR",
            basis=basis,
            calculation_trace=calc_trace,
            source_finding_id=finding_id,
            confidence=0.85,
            status="CALCULATED",
            is_additive=True,
            is_overlapping=False,
            is_informational=False,
        )

    def convert_impact_to_traces(self, impact: FinancialImpact) -> List[ExposureTrace]:
        """Convert a FinancialImpact instance into canonical ExposureTrace instances."""
        traces: List[ExposureTrace] = []
        if impact.calculation_status == CalculationStatus.NOT_APPLICABLE:
            return traces

        if impact.impact_type == FinancialImpactType.TAX_RATE_DIFFERENCE:
            taxable = impact.taxable_value or Decimal("0.00")
            rec_rate = impact.recorded_rate or Decimal("0.00")
            exp_rate = impact.expected_rate or Decimal("0.00")
            rec_tax = impact.recorded_tax or Decimal("0.00")
            exp_tax = impact.expected_tax or Decimal("0.00")
            traces.append(
                self.create_tax_difference_trace(
                    finding_id=impact.rule_id,
                    taxable_value=taxable,
                    recorded_rate=rec_rate,
                    expected_rate=exp_rate,
                    recorded_tax=rec_tax,
                    expected_tax=exp_tax,
                )
            )

        elif impact.impact_type == FinancialImpactType.ITC_EXPOSURE:
            amt = impact.potential_exposure or impact.recorded_tax or Decimal("0.00")
            if amt > Decimal("0.00"):
                traces.append(
                    self.create_itc_at_risk_trace(
                        finding_id=impact.rule_id,
                        blocked_tax_amount=amt,
                    )
                )

        else:
            amt = impact.potential_exposure or Decimal("0.00")
            if amt > Decimal("0.00"):
                calc_t = {
                    "formula": "Direct quantified exposure",
                    "inputs": {"potential_exposure": float(amt)},
                    "result": float(amt),
                }
                traces.append(
                    ExposureTrace(
                        exposure_type=CanonicalExposureType.POTENTIAL_TAX_EXPOSURE.value,
                        amount=amt,
                        currency=impact.currency,
                        basis=impact.calculation_basis or impact.reason or "Quantified potential exposure",
                        calculation_trace=calc_t,
                        source_finding_id=impact.rule_id,
                        confidence=impact.confidence,
                        status=impact.calculation_status.value,
                        is_additive=True,
                        is_overlapping=False,
                    )
                )

        return traces

    def summarize_case_exposure(
        self,
        case_id: str,
        invoice_id: str,
        traces: List[ExposureTrace],
    ) -> CaseFinancialSummary:
        """
        Build a double-count safe case financial exposure summary.
        Separates additive, overlapping, and informational exposure totals.
        """
        additive_tot = Decimal("0.00")
        overlapping_tot = Decimal("0.00")
        info_tot = Decimal("0.00")
        by_type: Dict[str, Decimal] = {}
        notes: List[str] = []

        for trace in traces:
            exp_type = trace.exposure_type
            by_type[exp_type] = by_type.get(exp_type, Decimal("0.00")) + trace.amount

            if trace.is_additive:
                additive_tot += trace.amount
            elif trace.is_overlapping:
                overlapping_tot += trace.amount
                notes.append(
                    f"Overlapping trace '{exp_type}' of INR {trace.amount:,.2f} is excluded from net exposure to prevent double counting."
                )
            elif trace.is_informational:
                info_tot += trace.amount
                notes.append(
                    f"Informational trace '{exp_type}' of INR {trace.amount:,.2f} recorded (not a net liability)."
                )

        net_exp = additive_tot

        if not notes:
            notes.append("Net financial exposure equals total additive exposure items.")

        return CaseFinancialSummary(
            case_id=case_id,
            invoice_id=invoice_id,
            additive_total=round_monetary(additive_tot),
            overlapping_total=round_monetary(overlapping_tot),
            informational_total=round_monetary(info_tot),
            net_financial_exposure=round_monetary(net_exp),
            currency="INR",
            traces=traces,
            by_type={k: round_monetary(v) for k, v in by_type.items()},
            summary_notes=notes,
        )
