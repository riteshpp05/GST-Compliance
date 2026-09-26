"""
UC15 GST Compliance Agent — Core Financial Impact Models (Sprint 6)
Defines deterministic models for quantifying potential financial exposure from compliance findings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional


class FinancialImpactType(str, Enum):
    """Categorization of financial impact drivers."""
    TAX_RATE_DIFFERENCE = "TAX_RATE_DIFFERENCE"
    ITC_EXPOSURE = "ITC_EXPOSURE"
    EWB_RELATED_EXPOSURE = "EWB_RELATED_EXPOSURE"
    DATA_QUALITY_EXPOSURE = "DATA_QUALITY_EXPOSURE"
    POTENTIAL_TAX_EXPOSURE = "POTENTIAL_TAX_EXPOSURE"
    TAX_DIFFERENCE = "TAX_DIFFERENCE"
    ITC_AT_RISK = "ITC_AT_RISK"
    POTENTIAL_INTEREST = "POTENTIAL_INTEREST"
    POTENTIAL_PENALTY = "POTENTIAL_PENALTY"
    TAX_OVERCHARGE = "TAX_OVERCHARGE"
    TAX_UNDERCHARGE = "TAX_UNDERCHARGE"
    OTHER = "OTHER"


class ImpactDirection(str, Enum):
    """Directional consequence of tax discrepancy."""
    OVERCHARGED_TAX = "OVERCHARGED_TAX"       # Recorded tax > Expected statutory tax (taxpayer / counterparty paid more)
    UNDERCHARGED_TAX = "UNDERCHARGED_TAX"     # Recorded tax < Expected statutory tax (potential recovery / statutory shortfall)
    NO_TAX_DIFFERENCE = "NO_TAX_DIFFERENCE"   # Rate / amount matches statutory schedule
    NOT_APPLICABLE = "NOT_APPLICABLE"         # Non-tax findings (e.g. documentation, process)


class CalculationStatus(str, Enum):
    """Deterministic calculation status of monetary exposure."""
    CALCULATED = "CALCULATED"                     # Full data available, mathematically quantified
    ESTIMATED = "ESTIMATED"                       # Estimated based on historical cohort or proxy metrics
    PARTIALLY_CALCULATED = "PARTIALLY_CALCULATED" # Some elements quantified, others missing
    UNDETERMINED = "UNDETERMINED"                 # Missing prerequisite data or no configured monetary formula
    NOT_APPLICABLE = "NOT_APPLICABLE"             # No monetary impact associated with this finding


def round_monetary(val: Decimal) -> Decimal:
    """Standard monetary rounding to 2 decimal places using ROUND_HALF_UP."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class FinancialImpact:
    """
    Deterministic quantification of potential financial exposure for an invoice finding.
    Never assumes legal liability or actual cash loss; expresses quantifiable potential exposure.
    """
    impact_id: str
    invoice_id: str
    invoice_date: Optional[date] = None
    counterparty_id: str = ""
    counterparty_name: str = ""
    rule_id: str = ""
    rule_category: str = ""
    impact_type: FinancialImpactType = FinancialImpactType.OTHER
    calculation_status: CalculationStatus = CalculationStatus.UNDETERMINED
    direction: ImpactDirection = ImpactDirection.NOT_APPLICABLE

    # Base Financial Values (Decimal precision)
    taxable_value: Optional[Decimal] = None
    recorded_rate: Optional[Decimal] = None
    expected_rate: Optional[Decimal] = None
    recorded_tax: Optional[Decimal] = None
    expected_tax: Optional[Decimal] = None
    tax_difference: Optional[Decimal] = None
    potential_exposure: Optional[Decimal] = None

    # Component-Level Breakdown (Optional)
    recorded_cgst: Optional[Decimal] = None
    expected_cgst: Optional[Decimal] = None
    cgst_difference: Optional[Decimal] = None
    recorded_sgst: Optional[Decimal] = None
    expected_sgst: Optional[Decimal] = None
    sgst_difference: Optional[Decimal] = None
    recorded_utgst: Optional[Decimal] = None
    expected_utgst: Optional[Decimal] = None
    utgst_difference: Optional[Decimal] = None
    recorded_igst: Optional[Decimal] = None
    expected_igst: Optional[Decimal] = None
    igst_difference: Optional[Decimal] = None
    recorded_cess: Optional[Decimal] = None
    expected_cess: Optional[Decimal] = None
    cess_difference: Optional[Decimal] = None

    @property
    def recorded_ugst(self) -> Optional[Decimal]:
        return self.recorded_utgst

    @property
    def expected_ugst(self) -> Optional[Decimal]:
        return self.expected_utgst

    @property
    def ugst_difference(self) -> Optional[Decimal]:
        return self.utgst_difference

    # Metadata & Explanations
    currency: str = "INR"
    calculation_basis: str = ""
    confidence: float = 1.0
    evidence: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None
    required_data: List[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def rate_difference_pct(self) -> Optional[Decimal]:
        if self.recorded_rate is not None and self.expected_rate is not None:
            return self.recorded_rate - self.expected_rate
        return None

    @property
    def undetermined_reason(self) -> Optional[str]:
        return self.reason

    def to_dict(self) -> Dict[str, Any]:
        """Serialize into clean dictionary representation."""
        return {
            "impact_id": self.impact_id,
            "invoice_id": self.invoice_id,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "counterparty_id": self.counterparty_id,
            "counterparty_name": self.counterparty_name,
            "rule_id": self.rule_id,
            "rule_category": self.rule_category,
            "impact_type": self.impact_type.value,
            "calculation_status": self.calculation_status.value,
            "direction": self.direction.value,
            "taxable_value": float(self.taxable_value) if self.taxable_value is not None else None,
            "recorded_rate": float(self.recorded_rate) if self.recorded_rate is not None else None,
            "expected_rate": float(self.expected_rate) if self.expected_rate is not None else None,
            "recorded_tax": float(self.recorded_tax) if self.recorded_tax is not None else None,
            "expected_tax": float(self.expected_tax) if self.expected_tax is not None else None,
            "tax_difference": float(self.tax_difference) if self.tax_difference is not None else None,
            "potential_exposure": float(self.potential_exposure) if self.potential_exposure is not None else None,
            "recorded_cgst": float(self.recorded_cgst) if self.recorded_cgst is not None else None,
            "expected_cgst": float(self.expected_cgst) if self.expected_cgst is not None else None,
            "cgst_difference": float(self.cgst_difference) if self.cgst_difference is not None else None,
            "recorded_sgst": float(self.recorded_sgst) if self.recorded_sgst is not None else None,
            "expected_sgst": float(self.expected_sgst) if self.expected_sgst is not None else None,
            "sgst_difference": float(self.sgst_difference) if self.sgst_difference is not None else None,
            "recorded_igst": float(self.recorded_igst) if self.recorded_igst is not None else None,
            "expected_igst": float(self.expected_igst) if self.expected_igst is not None else None,
            "igst_difference": float(self.igst_difference) if self.igst_difference is not None else None,
            "currency": self.currency,
            "calculation_basis": self.calculation_basis,
            "confidence": self.confidence,
            "reason": self.reason,
            "required_data": self.required_data,
            "evidence": self.evidence,
            "evaluated_at": self.evaluated_at,
        }
