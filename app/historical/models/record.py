"""
UC15 GST Compliance Agent — Historical Record Model (Sprint 5)
Normalized record representing an executed compliance decision with full audit metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from app.domain.models.validation import ComplianceDecision, ValidationResult


@dataclass
class HistoricalRecord:
    """
    Normalized, immutable representation of an evaluated invoice transaction
    used as the canonical unit for historical time-series aggregation and audit.
    """
    invoice_id: str
    invoice_date: date
    direction: str = "AR"                  # "AR" (outward/sales) | "AP" (inward/purchases)
    supplier_gstin: str = ""
    supplier_name: str = ""
    customer_gstin: str = ""
    customer_name: str = ""
    counterparty_gstin: str = ""
    counterparty_name: str = ""
    place_of_supply: str = ""
    hsn_code: str = ""
    item_desc: str = ""
    taxable_value: Decimal = Decimal("0.00")
    total_tax: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")

    # Compliance Verdict & Gate Results
    compliance_status: str = "COMPLIANT"    # COMPLIANT | NEEDS_REVIEW | NON_COMPLIANT
    failed_gate_count: int = 0
    failed_rule_ids: List[str] = field(default_factory=list)
    failed_gate_numbers: List[int] = field(default_factory=list)
    gate_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Data Quality findings (from Gate 1 or ingestion normalizer)
    data_quality_findings: List[str] = field(default_factory=list)

    # Risk Engine outcomes
    risk_level: Optional[str] = None       # LOW | MODERATE | MEDIUM | HIGH | CRITICAL
    risk_priority: Optional[str] = None    # P1 | P2 | P3 | P4
    risk_score: Optional[float] = None
    confidence: Optional[float] = None

    # Reference intelligence versions active when evaluated
    reference_versions: Dict[str, str] = field(default_factory=dict)
    unresolved_references: Dict[str, Any] = field(default_factory=dict)

    # Audit lineage
    audit_trail_ref: str = ""
    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Aliases for Section 6 compliance
    @property
    def transaction_type(self) -> str:
        return self.direction

    @property
    def validation_status(self) -> str:
        return self.compliance_status

    @property
    def failed_gates(self) -> List[int]:
        return self.failed_gate_numbers

    @classmethod
    def from_compliance_decision(
        cls,
        decision: ComplianceDecision,
        invoice: Optional[Any] = None,
    ) -> HistoricalRecord:
        """
        Construct a normalized HistoricalRecord from a ComplianceDecision and optional source Invoice.
        """
        # Parse invoice_date safely to date
        inv_date = getattr(decision, "invoice_date", None)
        if not inv_date:
            inv_date = date(2023, 1, 1)
        elif isinstance(inv_date, str):
            try:
                inv_date = date.fromisoformat(inv_date[:10])
            except Exception:
                inv_date = date(2023, 1, 1)
        elif isinstance(inv_date, datetime):
            inv_date = inv_date.date()
        elif not isinstance(inv_date, date):
            inv_date = date(2023, 1, 1)

        # Extract failed rules and gates
        failed_rule_ids: List[str] = []
        failed_gate_numbers: List[int] = []
        gate_results_dict: Dict[str, Dict[str, Any]] = {}

        for g in getattr(decision, "gates", []):
            gate_results_dict[g.rule_id] = {
                "rule_name": g.rule_name,
                "status": g.status,
                "message": g.message,
                "category": g.category,
                "severity": g.severity,
                "gate_no": g.gate_no,
                "actual_value": str(g.actual_value) if g.actual_value is not None else None,
                "expected_value": str(g.expected_value) if g.expected_value is not None else None,
            }
            if g.status == "FAIL":
                failed_rule_ids.append(g.rule_id)
                if g.gate_no is not None:
                    failed_gate_numbers.append(g.gate_no)

        # Extract DQ findings
        dq_findings: List[str] = []
        for dq in getattr(decision, "data_quality_results", []):
            if dq.status in ("FAIL", "WARNING", "NEEDS_REVIEW"):
                dq_findings.append(dq.message or dq.rule_name)

        # Check Gate 1 GSTIN format as a DQ issue if failed
        for g in getattr(decision, "gates", []):
            if getattr(g, "gate_no", None) == 1 and g.status == "FAIL":
                if "GSTIN format" not in dq_findings:
                    dq_findings.append(f"GSTIN format invalid: {decision.counterparty_gstin}")

        # Extract party information
        supplier_gstin = ""
        supplier_name = ""
        customer_gstin = ""
        customer_name = ""

        if invoice:
            supplier_gstin = getattr(invoice, "seller_gstin", "") or getattr(invoice, "supplier_gstin", "")
            customer_gstin = getattr(invoice, "buyer_gstin", "") or getattr(invoice, "customer_gstin", "")
            if hasattr(invoice, "vendor") and invoice.vendor:
                supplier_name = getattr(invoice.vendor, "name", "")
            if hasattr(invoice, "customer") and invoice.customer:
                customer_name = getattr(invoice.customer, "name", "")

        direction = getattr(decision, "direction", "AR")
        if direction == "AP":
            supplier_gstin = supplier_gstin or decision.counterparty_gstin
            supplier_name = supplier_name or decision.counterparty_name
        else:
            customer_gstin = customer_gstin or decision.counterparty_gstin
            customer_name = customer_name or decision.counterparty_name

        # Extract reference versions from snapshot if attached
        ref_versions: Dict[str, str] = {}
        unresolved: Dict[str, Any] = {}
        snap = getattr(decision, "reference_snapshot", None)
        if snap:
            refs = getattr(snap, "references", {})
            for rk, rv in refs.items():
                ref_versions[rk] = getattr(rv, "version", "1.0")
            unresolved = dict(getattr(snap, "unresolved", {}))

        # Financial values
        taxable_val = Decimal(str(getattr(decision, "taxable_value_inr", 0.0)))
        total_amt = Decimal(str(getattr(decision, "total_amt", 0.0)))
        total_tax = total_amt - taxable_val if total_amt >= taxable_val else Decimal("0.00")

        return cls(
            invoice_id=decision.invoice_no,
            invoice_date=inv_date,
            direction=direction,
            supplier_gstin=supplier_gstin,
            supplier_name=supplier_name,
            customer_gstin=customer_gstin,
            customer_name=customer_name,
            counterparty_gstin=decision.counterparty_gstin,
            counterparty_name=decision.counterparty_name,
            place_of_supply=decision.place_of_supply,
            hsn_code=decision.hsn_code,
            item_desc=decision.item_desc,
            taxable_value=taxable_val,
            total_tax=total_tax,
            total_amount=total_amt,
            compliance_status=decision.status,
            failed_gate_count=decision.failed_gate_count,
            failed_rule_ids=failed_rule_ids,
            failed_gate_numbers=failed_gate_numbers,
            gate_results=gate_results_dict,
            data_quality_findings=dq_findings,
            risk_level=decision.risk_level,
            risk_priority=decision.priority,
            risk_score=decision.risk_score,
            confidence=getattr(decision, "confidence", 1.0),
            reference_versions=ref_versions,
            unresolved_references=unresolved,
            audit_trail_ref=decision.audit_trail_ref,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "invoice_date": self.invoice_date.isoformat(),
            "direction": self.direction,
            "supplier_gstin": self.supplier_gstin,
            "supplier_name": self.supplier_name,
            "customer_gstin": self.customer_gstin,
            "customer_name": self.customer_name,
            "counterparty_gstin": self.counterparty_gstin,
            "counterparty_name": self.counterparty_name,
            "place_of_supply": self.place_of_supply,
            "hsn_code": self.hsn_code,
            "item_desc": self.item_desc,
            "taxable_value": float(self.taxable_value),
            "total_tax": float(self.total_tax),
            "total_amount": float(self.total_amount),
            "compliance_status": self.compliance_status,
            "validation_status": self.validation_status,
            "transaction_type": self.transaction_type,
            "failed_gate_count": self.failed_gate_count,
            "failed_rule_ids": self.failed_rule_ids,
            "failed_gates": self.failed_gates,
            "failed_gate_numbers": self.failed_gate_numbers,
            "gate_results": self.gate_results,
            "data_quality_findings": self.data_quality_findings,
            "risk_level": self.risk_level,
            "risk_priority": self.risk_priority,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "reference_versions": self.reference_versions,
            "unresolved_references": self.unresolved_references,
            "audit_trail_ref": self.audit_trail_ref,
            "evaluated_at": self.evaluated_at,
        }
