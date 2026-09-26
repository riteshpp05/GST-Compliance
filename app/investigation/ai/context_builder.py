"""
UC15 GST Compliance Agent — Canonical AI Investigation Context Builder (Sprint 23)
Constructs bounded, source-grounded investigation contexts for downstream AI analysis.
Ensures AI receives only approved, structured data with unique source IDs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.engines.financial_engine import FinancialExposureEngine
from app.investigation.evidence.sufficiency_evaluator import EvidenceSufficiencyEvaluator
from app.reconciliation.engine import ReconciliationEngine


@dataclass
class ControlledInvestigationContext:
    """
    Canonical structured context provided to AI for grounded investigation synthesis.
    Every element possesses a unique, verifiable source ID.
    """
    case_id: str
    invoice_id: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    financial_exposures: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    reconciliation_results: Dict[str, Any] = field(default_factory=dict)
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    missing_evidence: List[Dict[str, Any]] = field(default_factory=list)
    reference_context: List[Dict[str, Any]] = field(default_factory=list)
    case_snapshot: Dict[str, Any] = field(default_factory=dict)
    context_schema_version: str = "v23.0"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "invoice_id": self.invoice_id,
            "findings": self.findings,
            "financial_exposures": self.financial_exposures,
            "evidence": self.evidence,
            "reconciliation_results": self.reconciliation_results,
            "contradictions": self.contradictions,
            "missing_evidence": self.missing_evidence,
            "reference_context": self.reference_context,
            "case_snapshot": self.case_snapshot,
            "context_schema_version": self.context_schema_version,
            "created_at": self.created_at,
        }

    def get_valid_source_ids(self) -> set[str]:
        """Collect all valid source IDs present in the context for evidence grounding validation."""
        s_ids = {self.case_id, self.invoice_id}
        for f in self.findings:
            if "finding_id" in f:
                s_ids.add(f["finding_id"])
            if "rule_id" in f:
                s_ids.add(f["rule_id"])
        for e in self.financial_exposures:
            if "exposure_id" in e:
                s_ids.add(e["exposure_id"])
            if "source_finding_id" in e and e["source_finding_id"]:
                s_ids.add(e["source_finding_id"])
        for ev in self.evidence:
            if "evidence_id" in ev:
                s_ids.add(ev["evidence_id"])
        for c in self.contradictions:
            if "contradiction_id" in c:
                s_ids.add(c["contradiction_id"])
        return s_ids


class CanonicalAIContextBuilder:
    """
    Builder orchestrating context construction across validation, financial, reconciliation,
    and evidence engines to construct ControlledInvestigationContext.
    """

    def __init__(
        self,
        financial_engine: Optional[FinancialExposureEngine] = None,
        reconciliation_engine: Optional[ReconciliationEngine] = None,
        sufficiency_evaluator: Optional[EvidenceSufficiencyEvaluator] = None,
    ) -> None:
        self.financial_engine = financial_engine or FinancialExposureEngine()
        self.reconciliation_engine = reconciliation_engine or ReconciliationEngine()
        self.sufficiency_evaluator = sufficiency_evaluator or EvidenceSufficiencyEvaluator()

    def build_context(
        self,
        case_id: str,
        invoice: Optional[Invoice] = None,
        decision: Optional[ComplianceDecision] = None,
        gstr2b_record: Optional[Dict[str, Any]] = None,
        supplier_master: Optional[Dict[str, Any]] = None,
    ) -> ControlledInvestigationContext:
        inv_id = (
            getattr(invoice, "invoice_id", None)
            or getattr(decision, "invoice_no", None)
            or case_id
        )

        # 1. Structure Findings with unique finding_ids
        findings_structured: List[Dict[str, Any]] = []
        if decision and getattr(decision, "gates", None):
            for idx, g in enumerate(decision.gates, 1):
                if g.status == "FAIL":
                    fid = f"FIND-{inv_id}-{g.rule_id}"
                    findings_structured.append({
                        "finding_id": fid,
                        "rule_id": g.rule_id,
                        "category": g.category or "STATUTORY",
                        "status": g.status,
                        "gate_no": g.gate_no,
                        "observed_value": str(g.actual_value) if g.actual_value is not None else None,
                        "expected_value": str(g.expected_value) if g.expected_value is not None else None,
                        "message": g.message or g.detail or "",
                    })

        if not findings_structured and decision:
            findings_structured.append({
                "finding_id": f"FIND-{inv_id}-CLEAN",
                "rule_id": "COMPLIANT",
                "category": "COMPLIANCE",
                "status": "PASS",
                "message": "All statutory compliance gates passed cleanly.",
            })

        # 2. Financial Exposure Traces
        traces = []
        if decision:
            impacts = self.financial_engine.tax_calc.calculate_invoice_impact(decision, invoice) if hasattr(self.financial_engine, "tax_calc") else []
            for imp in impacts:
                traces.extend(self.financial_engine.convert_impact_to_traces(imp))

        exposures_structured: List[Dict[str, Any]] = []
        for idx, tr in enumerate(traces, 1):
            exp_id = f"EXP-{inv_id}-{tr.exposure_type}-{idx}"
            exp_dict = tr.to_dict()
            exp_dict["exposure_id"] = exp_id
            exposures_structured.append(exp_dict)

        # 3. Evidence Records
        evidence_structured: List[Dict[str, Any]] = []
        if invoice:
            evidence_structured.append({
                "evidence_id": f"EVD-{inv_id}-INVOICE",
                "evidence_type": "INVOICE_HEADER",
                "description": f"Invoice {inv_id} date {invoice.invoice_date} counterparty {invoice.counterparty_name} ({invoice.gstin})",
                "source": "INVOICE_PAYLOAD",
                "provenance": {"invoice_id": inv_id, "direction": invoice.direction},
            })

        if gstr2b_record:
            evidence_structured.append({
                "evidence_id": f"EVD-{inv_id}-GSTR2B",
                "evidence_type": "GSTR2B_STATEMENT",
                "description": f"GSTR-2B filing statement record for {inv_id}",
                "source": "GSTR2B_PORTAL_INGESTION",
                "provenance": gstr2b_record,
            })

        if supplier_master:
            evidence_structured.append({
                "evidence_id": f"EVD-{inv_id}-SUPPLIER-MASTER",
                "evidence_type": "ERP_VENDOR_MASTER",
                "description": f"Supplier ERP master record for {supplier_master.get('name', 'Vendor')}",
                "source": "SAP_VENDOR_MASTER",
                "provenance": supplier_master,
            })

        # 4. Multi-way Reconciliation & Contradictions
        rec_res = self.reconciliation_engine.reconcile(
            case_id=case_id,
            invoice=invoice,
            decision=decision,
            gstr2b_record=gstr2b_record,
            supplier_master=supplier_master,
        )
        rec_dict = rec_res.to_dict()
        contradictions_structured = [c.to_dict() for c in rec_res.contradictions]

        # 5. Missing Evidence
        suff_report = self.sufficiency_evaluator.evaluate(
            case_id=case_id,
            invoice=invoice,
            decision=decision,
            reconciliation_result=rec_res,
        )
        missing_structured = [m.to_dict() for m in suff_report.missing_evidence_items]

        # 6. Statutory Reference Context
        ref_context = [
            {
                "reference_id": "TAX_RATE_REF_V1",
                "hsn_code": invoice.hsn_sac if invoice else "8471",
                "statutory_rate": 18.0 if (invoice and invoice.hsn_sac == "8471") else 18.0,
                "effective_from": "2017-07-01",
                "effective_to": "2025-09-21",
            }
        ]

        # 7. Case Snapshot
        snapshot = {
            "case_id": case_id,
            "invoice_id": inv_id,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "rule_version": "v21.0_canonical",
        }

        return ControlledInvestigationContext(
            case_id=case_id,
            invoice_id=inv_id,
            findings=findings_structured,
            financial_exposures=exposures_structured,
            evidence=evidence_structured,
            reconciliation_results=rec_dict,
            contradictions=contradictions_structured,
            missing_evidence=missing_structured,
            reference_context=ref_context,
            case_snapshot=snapshot,
        )
