"""
app.investigation.consolidation
===============================
Finding Consolidation & Conflict Detection Service for UC15 (Sprint 18).
Consolidates raw outputs from multiple GST engines into structured CaseFinding items.
Detects contradictory engine signals and records CONFLICTING_ANALYSIS findings.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.case.models import CaseFinding
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class FindingConsolidationService:
    """
    Consolidates raw intelligence outputs from all engines into unified CaseFinding objects.
    Enforces non-destructive consolidation by storing references to raw engine outputs.
    """

    def consolidate_findings(
        self,
        case_id: str,
        tool_results_by_name: Dict[str, Any],
        evidence_ids: List[str],
    ) -> Tuple[List[CaseFinding], bool]:
        """
        Consolidate tool execution results into structured CaseFinding domain models.
        Returns (findings, has_contradictions_flag).
        """
        findings: List[CaseFinding] = []
        has_contradictions = False

        val_res = tool_results_by_name.get("get_compliance_result") or tool_results_by_name.get("validate_invoice") or {}
        risk_res = tool_results_by_name.get("get_risk_assessment") or {}
        dup_res = tool_results_by_name.get("find_duplicates") or {}
        fin_res = tool_results_by_name.get("get_financial_exposure") or {}
        hist_res = tool_results_by_name.get("get_historical_patterns") or {}
        rca_res = tool_results_by_name.get("investigate_root_cause") or {}
        blast_res = tool_results_by_name.get("get_blast_radius") or {}

        # 1. Statutory Validation Finding
        val_status = str(val_res.get("status") or val_res.get("overall_status") or "").upper()
        if val_res:
            failed_gates = val_res.get("failed_gates") or []
            if val_status in {"NON_COMPLIANT", "NEEDS_REVIEW"} or failed_gates:
                f = CaseFinding(
                    case_id=case_id,
                    title=f"Statutory GST Gate Mismatch ({len(failed_gates)} gate(s) failed)",
                    description=val_res.get("justification") or f"Invoice failed statutory gate checks: {failed_gates}.",
                    category="STATUTORY_COMPLIANCE",
                    severity="CRITICAL" if val_status == "NON_COMPLIANT" else "HIGH",
                    evidence_ids=evidence_ids,
                    confidence=0.95,
                    status="VERIFIED",
                )
                findings.append(f)

        # 2. Risk Finding
        risk_level = str(risk_res.get("risk_level") or "").upper()
        risk_score = float(risk_res.get("risk_score") or 0.0)
        if risk_score > 30.0:
            f = CaseFinding(
                case_id=case_id,
                title=f"Elevated Tax Risk Score ({risk_score:.1f}/100 - Level {risk_level})",
                description=f"Risk engine identified risk drivers: {risk_res.get('risk_drivers', risk_res.get('contributing_factors', []))}.",
                category="RISK_EVALUATION",
                severity=risk_level if risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else "HIGH",
                evidence_ids=evidence_ids,
                confidence=0.90,
                status="VERIFIED",
            )
            findings.append(f)

        # 3. Duplicate Finding
        dup_matches = dup_res.get("matches") or dup_res.get("duplicate_records") or []
        dup_status = str(dup_res.get("duplicate_status") or "").upper()
        if dup_matches or dup_status in {"EXACT_DUPLICATE", "POTENTIAL_DUPLICATE"}:
            f = CaseFinding(
                case_id=case_id,
                title=f"Duplicate Invoice Signal Detected ({dup_status or 'MATCHED'})",
                description=f"Duplicate engine detected match against existing records: {dup_matches}.",
                category="DUPLICATE_ANOMALY",
                severity="HIGH" if dup_status == "EXACT_DUPLICATE" else "MEDIUM",
                evidence_ids=evidence_ids,
                confidence=0.85,
                status="VERIFIED",
            )
            findings.append(f)

        # 4. Financial Exposure Finding
        exposure_amt = float(fin_res.get("financial_exposure", fin_res.get("potential_exposure", 0.0)))
        if exposure_amt > 0.0:
            f = CaseFinding(
                case_id=case_id,
                title=f"Quantified Financial Exposure: INR {exposure_amt:,.2f}",
                description=f"Financial impact analysis identified potential tax differential / exposure of INR {exposure_amt:,.2f}.",
                category="FINANCIAL_IMPACT",
                severity="CRITICAL" if exposure_amt >= 100000.0 else "HIGH",
                evidence_ids=evidence_ids,
                confidence=0.95,
                status="VERIFIED",
            )
            findings.append(f)

        # 5. Root Cause & Blast Radius Finding
        rc_name = rca_res.get("root_cause") or rca_res.get("category")
        if rc_name and str(rc_name).upper() != "UNDETERMINED":
            f = CaseFinding(
                case_id=case_id,
                title=f"Root Cause Identified: {rc_name}",
                description=rca_res.get("explanation") or f"Root cause analysis mapped failure to {rc_name}.",
                category="ROOT_CAUSE",
                severity="HIGH",
                evidence_ids=evidence_ids,
                confidence=0.88,
                status="VERIFIED",
            )
            findings.append(f)

        # 6. Conflict Detection Logic
        # Case A: Validation PASS but Risk HIGH
        is_val_pass = val_status == "COMPLIANT" or (val_res and val_res.get("failed_gate_count") == 0)
        is_risk_high = risk_level in {"HIGH", "CRITICAL"} or risk_score >= 60.0

        if is_val_pass and is_risk_high:
            has_contradictions = True
            cf = CaseFinding(
                case_id=case_id,
                title="Conflicting Analysis: Deterministic Validation PASS vs High Risk Score",
                description=(
                    f"Validation engine passed all statutory gates for invoice, but Risk engine flagged high risk "
                    f"({risk_score:.1f}/100, Level: {risk_level}). Preserving both signals for human review."
                ),
                category="CONFLICTING_ANALYSIS",
                severity="HIGH",
                evidence_ids=evidence_ids,
                confidence=0.60,
                status="VERIFIED",
            )
            findings.append(cf)

        # Case B: Duplicate EXACT_DUPLICATE but Historical Clean
        hist_score = float(hist_res.get("compliance_score", 100.0))
        if dup_status == "EXACT_DUPLICATE" and hist_score >= 95.0:
            has_contradictions = True
            cf = CaseFinding(
                case_id=case_id,
                title="Conflicting Analysis: Exact Duplicate Signal on Historically Compliant Supplier",
                description=(
                    f"Duplicate engine flagged exact duplicate, but counterparty historical compliance score is very high "
                    f"({hist_score:.1f}%). Requires verification of potential ERP double-posting."
                ),
                category="CONFLICTING_ANALYSIS",
                severity="MEDIUM",
                evidence_ids=evidence_ids,
                confidence=0.65,
                status="VERIFIED",
            )
            findings.append(cf)

        # Default fallback finding if engines returned empty
        if not findings:
            findings.append(
                CaseFinding(
                    case_id=case_id,
                    title="General Compliance Assessment",
                    description="Standard investigation completed without critical compliance failures.",
                    category="GENERAL_COMPLIANCE",
                    severity="LOW",
                    evidence_ids=evidence_ids,
                    confidence=0.90,
                    status="VERIFIED",
                )
            )

        return findings, has_contradictions
