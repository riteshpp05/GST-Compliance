"""
app.agent.ai.dossier
====================
Investigation Dossier Building Engine for UC15 (Sprint 12.4).
Consolidates multi-turn session evidence, statutory gate determinations, financial exposure,
root cause & blast radius analysis, regulatory document citations, and advisory SAP/finance guidance
into structured audit dossiers with JSON, Markdown, and PDF output capabilities.
Enforces strict evidence provenance and explicit 'INSUFFICIENT EVIDENCE / NOT AVAILABLE' notices.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agent.ai.session import EntityFocus, InvestigationSession
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class InvestigationDossier(BaseModel):
    """
    Evidence-backed Audit Dossier domain model.
    Contains complete statutory, financial, intelligence, and regulatory evidence context.
    """
    dossier_id: str = Field(..., description="Unique dossier ID (e.g. DOSSIER-SESS-ABCD1234).")
    session_id: str = Field(..., description="Associated multi-turn investigation session ID.")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of dossier generation.",
    )
    entity_focus: EntityFocus = Field(default_factory=EntityFocus, description="Target entity focus scope.")
    executive_summary: str = Field(..., description="High-level audit executive summary and compliance verdict.")
    session_history: List[Dict[str, Any]] = Field(default_factory=list, description="Chronological query and turn history.")
    gate_breakdown: List[Dict[str, Any]] = Field(default_factory=list, description="Gates 1-6 compliance validation details.")
    risk_assessment: Dict[str, Any] = Field(default_factory=dict, description="Risk profile, risk score, and severity drivers.")
    financial_exposure: Dict[str, Any] = Field(default_factory=dict, description="Financial exposure calculation breakdown.")
    root_cause_analysis: Dict[str, Any] = Field(default_factory=dict, description="Primary root cause and causality statement.")
    blast_radius_analysis: Dict[str, Any] = Field(default_factory=dict, description="Multidimensional blast radius impact scope.")
    regulatory_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved GST statutory rules and provenance citations.")
    advisory_recommendations: List[str] = Field(default_factory=list, description="Advisory SAP / Finance action recommendations.")
    audit_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Audit execution trace log.")
    insufficient_evidence_notices: List[str] = Field(default_factory=list, description="Explicit notices for missing evidence dimensions.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert dossier to standard serializable dictionary."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Serialize dossier to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def to_markdown(self) -> str:
        """Render complete, audit-ready GitHub-flavored Markdown report."""
        lines: List[str] = []
        sep = "=" * 80
        thin_sep = "-" * 80

        lines.append("# UC15 GST COMPLIANCE & INVESTIGATION DOSSIER")
        lines.append(f"**Dossier ID:** `{self.dossier_id}` | **Session ID:** `{self.session_id}` | **Generated:** {self.generated_at}")
        lines.append(f"**Target Scope:** {self.entity_focus.summary_string()}")
        lines.append("")
        lines.append(sep)
        lines.append("## 1. EXECUTIVE SUMMARY & AUDIT VERDICT")
        lines.append(sep)
        lines.append(self.executive_summary)
        lines.append("")

        if self.insufficient_evidence_notices:
            lines.append("> [!WARNING]")
            lines.append("> **EVIDENCE NOTICES & LIMITATIONS:**")
            for notic in self.insufficient_evidence_notices:
                lines.append(f"> - {notic}")
            lines.append("")

        # 2. Multi-Turn Session History
        lines.append(sep)
        lines.append("## 2. MULTI-TURN INVESTIGATION SESSION TRAIL")
        lines.append(sep)
        if not self.session_history:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: No query turns recorded in session.*")
        else:
            for turn in self.session_history:
                lines.append(f"### Turn #{turn.get('turn_index')}: '{turn.get('user_query')}'")
                lines.append(f"- **Resolved Query:** {turn.get('resolved_query')}")
                lines.append(f"- **Intent:** `{turn.get('intent')}` | **Tools Called:** {', '.join(turn.get('tools_used', []))}")
                lines.append(f"- **Synthesized Answer Excerpt:**\n  > {turn.get('synthesized_answer', '')[:200]}...")
                lines.append("")

        # 3. Compliance Gate Results
        lines.append(sep)
        lines.append("## 3. STATUTORY COMPLIANCE GATE RESULTS (GATES 1-6)")
        lines.append(sep)
        if not self.gate_breakdown:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: No specific gate results evaluated for target.*")
        else:
            for inv in self.gate_breakdown:
                inv_no = inv.get("invoice_no") or inv.get("invoice_id") or "Target"
                status = inv.get("compliance_status") or inv.get("status") or "UNKNOWN"
                lines.append(f"### Invoice {inv_no} — Verdict: `{status}`")
                gates = inv.get("gates") or inv.get("gate_results") or []
                if not gates:
                    lines.append("- *Gate breakdown details unavailable.*")
                else:
                    for g in gates:
                        g_num = g.get("gate_number") or g.get("gate")
                        g_name = g.get("gate_name") or g.get("name")
                        g_stat = g.get("status") or g.get("result")
                        g_msg = g.get("message") or g.get("details", "")
                        lines.append(f"- **Gate {g_num} [{g_name}]:** `{g_stat}` — {g_msg}")
                lines.append("")

        # 4. Risk Profile & Financial Exposure
        lines.append(sep)
        lines.append("## 4. RISK PROFILE & FINANCIAL EXPOSURE ANALYSIS")
        lines.append(sep)
        if self.risk_assessment:
            score = self.risk_assessment.get("risk_score") or self.risk_assessment.get("score") or "N/A"
            level = self.risk_assessment.get("risk_level") or self.risk_assessment.get("level") or "N/A"
            prio = self.risk_assessment.get("risk_priority") or self.risk_assessment.get("priority") or "N/A"
            lines.append(f"**Risk Profile:** `{level}` | **Score:** `{score}/100` | **Priority:** `{prio}`")
            drivers = self.risk_assessment.get("risk_drivers") or []
            if drivers:
                lines.append("**Primary Risk Drivers:**")
                for d in drivers:
                    lines.append(f"- {d.get('driver_code')} ({d.get('severity')}): +{d.get('weight')} ({d.get('category')})")
        else:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: Risk assessment not executed for target.*")

        lines.append("")
        if self.financial_exposure:
            tot = self.financial_exposure.get("total_potential_exposure") or self.financial_exposure.get("total_exposure") or 0.0
            itc = self.financial_exposure.get("itc_at_risk") or 0.0
            tax_diff = self.financial_exposure.get("tax_mismatch_exposure") or 0.0
            lines.append(f"**Financial Exposure Engine:** INR {tot:,.2f}")
            lines.append(f"- **ITC at Risk:** INR {itc:,.2f}")
            lines.append(f"- **Tax Mismatch Exposure:** INR {tax_diff:,.2f}")
        else:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: Financial exposure calculation not available.*")
        lines.append("")

        # 5. Root Cause & Blast Radius Analysis
        lines.append(sep)
        lines.append("## 5. ROOT CAUSE & BLAST RADIUS INTELLIGENCE")
        lines.append(sep)
        if self.root_cause_analysis:
            rc_type = self.root_cause_analysis.get("root_cause_type") or self.root_cause_analysis.get("title") or "N/A"
            conf = self.root_cause_analysis.get("confidence") or "N/A"
            stmt = self.root_cause_analysis.get("causality_statement") or "N/A"
            lines.append(f"**Primary Root Cause:** {rc_type} (Confidence: {conf})")
            lines.append(f"**Causality Statement:** *\"{stmt}\"*")
        else:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: Root cause intelligence not evaluated.*")

        lines.append("")
        if self.blast_radius_analysis:
            sys_cls = self.blast_radius_analysis.get("systemic_classification") or "N/A"
            aff_inv = self.blast_radius_analysis.get("affected_invoice_count") or 0
            aff_cp = self.blast_radius_analysis.get("affected_counterparty_count") or 0
            trend = self.blast_radius_analysis.get("trend") or "N/A"
            lines.append(f"**Systemic Classification:** `{sys_cls}` | **Trend:** `{trend}`")
            lines.append(f"- **Affected Invoices:** {aff_inv} | **Affected Counterparties:** {aff_cp}")
        else:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: Blast radius impact not evaluated.*")
        lines.append("")

        # 6. Regulatory Grounding & Statutory Provenance
        lines.append(sep)
        lines.append("## 6. REGULATORY GROUNDING & STATUTORY PROVENANCE")
        lines.append(sep)
        if not self.regulatory_evidence:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: No regulatory knowledge documents retrieved.*")
        else:
            for idx, ev in enumerate(self.regulatory_evidence, 1):
                prov = ev.get("provenance", {})
                doc_n = prov.get("document_name") or "Statutory Document"
                loc = f"Page {prov.get('page_number')}" if prov.get("page_number") else f"Sec: {prov.get('section') or 'General'}"
                score = ev.get("relevance_score") or 0.0
                eff_f = prov.get("effective_from") or "ALL"
                eff_t = prov.get("effective_to") or "ONGOING"
                lines.append(f"### {idx}. [{ev.get('status', 'SUPPORTED')}] {doc_n} ({loc})")
                lines.append(f"- **Provenance:** Doc ID: `{prov.get('document_id')}` | Source: `{prov.get('source')}` | Relevance: `{score}`")
                lines.append(f"- **Effective Dates:** `{eff_f}` to `{eff_t}`")
                excerpt = ev.get("chunk", {}).get("content") or ""
                if excerpt:
                    lines.append(f"- **Excerpt:** *\"{excerpt[:250]}...\"*")
                lines.append("")

        # 7. Advisory Resolution Recommendations & SAP Guidance
        lines.append(sep)
        lines.append("## 7. ADVISORY RESOLUTION ACTIONS & SAP GUIDANCE")
        lines.append(sep)
        lines.append("> [!NOTE]")
        lines.append("> **ADVISORY NOTICE:** The following SAP / Finance action recommendations are ADVISORY GUIDANCE ONLY.")
        lines.append("> UC15 does not perform live SAP API calls, RFC, OData mutations, or posting actions.")
        lines.append("")
        if not self.advisory_recommendations:
            lines.append("- Review compliance discrepancy details with tax team before GSTR-1/3B filing.")
        else:
            for rec in self.advisory_recommendations:
                lines.append(f"- {rec}")
        lines.append("")

        # 8. Appendices & Audit Execution Trace
        lines.append(sep)
        lines.append("## 8. APPENDICES & AUDIT EXECUTION TRACE")
        lines.append(sep)
        if not self.audit_trace:
            lines.append("*INSUFFICIENT EVIDENCE / NOT AVAILABLE: Audit trace step log unavailable.*")
        else:
            for s in self.audit_trace[:10]:
                lines.append(f"- **Step #{s.get('step_number')}:** `{s.get('action_type')}` ({s.get('tool_name') or 'N/A'}) -> {s.get('result_summary')}")

        lines.append("")
        lines.append(sep + "\n")
        return "\n".join(lines)


class DossierBuilder:
    """
    Constructs an evidence-backed InvestigationDossier from an InvestigationSession.
    Extracts deterministic Findings, Gate results, Financial Exposure, Root Cause,
    Blast Radius, Regulatory Evidence, and Advisory Recommendations while preserving provenance.
    """

    @staticmethod
    def build_dossier(session: InvestigationSession) -> InvestigationDossier:
        """Build structured InvestigationDossier from session state."""
        dossier_id = f"DOSSIER-{session.session_id}"
        focus = session.entity_focus
        history = [turn.model_dump() for turn in session.turns]

        # Consolidated findings and regulatory evidence across turns
        findings = session.accumulated_findings
        reg_evidence = session.accumulated_regulatory_evidence
        notices: List[str] = []

        # Extract dimensions from findings
        gate_breakdown: List[Dict[str, Any]] = []
        risk_summary: Dict[str, Any] = {}
        fin_exposure: Dict[str, Any] = {}
        root_cause: Dict[str, Any] = {}
        blast_radius: Dict[str, Any] = {}
        advisory_recs: List[str] = []
        audit_trace: List[Dict[str, Any]] = []

        for turn in session.turns:
            for f in turn.findings:
                f_type = f.get("type", "")
                data = f.get("data") or f
                if f_type == "COMPLIANCE_RESULT" or "gates" in data:
                    if isinstance(data, list):
                        gate_breakdown.extend(data)
                    elif isinstance(data, dict):
                        gate_breakdown.append(data)
                elif f_type == "RISK_ASSESSMENT" or "risk_score" in data:
                    risk_summary = data
                elif f_type == "FINANCIAL_EXPOSURE" or "total_potential_exposure" in data or "total_exposure" in data:
                    fin_exposure = data
                elif f_type == "ROOT_CAUSE_ANALYSIS" or "root_cause_type" in data:
                    root_cause = data
                elif f_type == "BLAST_RADIUS" or "systemic_classification" in data:
                    blast_radius = data

            # Extract advisory recommendations from turn answers
            if "SAP action:" in turn.synthesized_answer:
                for line in turn.synthesized_answer.split("\n"):
                    if "SAP action:" in line:
                        advisory_recs.append(line.strip())

        # Check for missing dimensions and record explicit notices
        if not gate_breakdown:
            notices.append("INSUFFICIENT EVIDENCE / NOT AVAILABLE: Statutory compliance gate validation not run for target.")
        if not risk_summary:
            notices.append("INSUFFICIENT EVIDENCE / NOT AVAILABLE: Risk assessment score unavailable for target.")
        if not fin_exposure:
            notices.append("INSUFFICIENT EVIDENCE / NOT AVAILABLE: Financial exposure calculation not available.")
        if not root_cause:
            notices.append("INSUFFICIENT EVIDENCE / NOT AVAILABLE: Root cause analysis not executed for target.")
        if not blast_radius:
            notices.append("INSUFFICIENT EVIDENCE / NOT AVAILABLE: Blast radius impact scope not calculated.")
        if not reg_evidence:
            notices.append("INSUFFICIENT EVIDENCE / NOT AVAILABLE: No statutory GST rules or CBIC circulars retrieved.")

        # Default advisory recommendations if none extracted
        if not advisory_recs:
            if focus.invoice_id:
                advisory_recs.append(f"ADVISORY: Hold invoice {focus.invoice_id} from GSTR-1/GSTR-3B filing pending multi-issue correction.")
            else:
                advisory_recs.append("ADVISORY: Hold flagged non-compliant invoices from GSTR filing cycle pending vendor reconciliation.")
            advisory_recs.append("ADVISORY: Issue formal GST compliance query to vendor regarding GSTR-2B reflection / POS alignment.")

        # Build Executive Summary
        exec_lines = [
            f"Investigation Dossier generated for session '{session.session_id}' covering target scope '{focus.summary_string()}'.",
            f"Total conversation turns executed: {len(session.turns)}. Accumulated deterministic findings: {len(findings)}.",
        ]
        if focus.invoice_id and gate_breakdown:
            inv_res = gate_breakdown[0]
            st = inv_res.get("compliance_status") or inv_res.get("status") or "EVALUATED"
            exec_lines.append(f"Target Invoice {focus.invoice_id} Compliance Status: {st}.")
        if fin_exposure:
            tot = fin_exposure.get("total_potential_exposure") or fin_exposure.get("total_exposure") or 0.0
            exec_lines.append(f"Total Evaluated Financial Exposure: INR {tot:,.2f}.")

        exec_summary = " ".join(exec_lines)

        return InvestigationDossier(
            dossier_id=dossier_id,
            session_id=session.session_id,
            entity_focus=focus,
            executive_summary=exec_summary,
            session_history=history,
            gate_breakdown=gate_breakdown,
            risk_assessment=risk_summary,
            financial_exposure=fin_exposure,
            root_cause_analysis=root_cause,
            blast_radius_analysis=blast_radius,
            regulatory_evidence=reg_evidence,
            advisory_recommendations=advisory_recs,
            audit_trace=audit_trace,
            insufficient_evidence_notices=notices,
        )
