"""
UC15 GST Compliance Agent — Run Summary & Optional LLM Narrative
"""
from __future__ import annotations

import os
from typing import List
from app.config.settings import settings
from app.domain.models.validation import ComplianceDecision
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class LLMSummarizer:
    """Provides human-readable summary narrative using fallback heuristics or optional LLM."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.llm_api_key or os.getenv("OPENAI_API_KEY", "")
        self.enabled = bool(self.api_key)

    def summarize_run(self, decisions: List[ComplianceDecision]) -> str:
        # For Sprint 1, safe deterministic fallback summary
        return self._fallback_summary(decisions)

    @staticmethod
    def _fallback_summary(decisions: List[ComplianceDecision]) -> str:
        total = len(decisions)
        compliant = sum(1 for d in decisions if d.status == "COMPLIANT")
        review = sum(1 for d in decisions if d.status == "NEEDS_REVIEW")
        blocked = sum(1 for d in decisions if d.status == "NON_COMPLIANT")
        rate = f"{100 * compliant / total:.0f}%" if total else "0%"
        return (
            f"Validated {total} invoices against GST compliance rules.\n"
            f"  {compliant} compliant and ready for GSTR filing ({rate}).\n"
            f"  {review} need review before this filing cycle.\n"
            f"  {blocked} blocked — non-compliant, require correction."
        )

    @staticmethod
    def generate_coverage_report(decisions: List[ComplianceDecision]) -> str:
        """Generates audit coverage report answering what UC15 verified across the batch."""
        total = len(decisions)
        total_controls = 0
        passed_controls = 0
        failed_controls = 0
        review_controls = 0
        na_controls = 0

        for d in decisions:
            for r in d.gate_results:
                total_controls += 1
                status = str(r.status).upper()
                if status == "PASS":
                    passed_controls += 1
                elif status in ("FAIL", "NON_COMPLIANT"):
                    failed_controls += 1
                elif status in ("NEEDS_REVIEW", "WARNING", "INSUFFICIENT_DATA"):
                    review_controls += 1
                elif status in ("NOT_APPLICABLE", "NEVER"):
                    na_controls += 1

        cov_rate = f"{100 * (passed_controls + review_controls) / total_controls:.1f}%" if total_controls else "0%"

        return (
            "======================================================================\n"
            "                 UC15 COMPLIANCE AUDIT COVERAGE REPORT                \n"
            "======================================================================\n"
            f"  Total Transactions Ingested & Analyzed : {total}\n"
            f"  Total Applicable Controls Executed     : {total_controls}\n"
            "----------------------------------------------------------------------\n"
            f"  • Passed Controls                      : {passed_controls}\n"
            f"  • Non-Compliant Controls                : {failed_controls}\n"
            f"  • Review / Insufficient Data Controls  : {review_controls}\n"
            f"  • Not Applicable Controls              : {na_controls}\n"
            "----------------------------------------------------------------------\n"
            f"  Audit Verification Coverage Index      : {cov_rate}\n"
            "  Domain Verification Scope              : GSTIN, HSN, POS, TAX, EWB, IRN, ITC, RCM\n"
            "======================================================================\n"
        )
