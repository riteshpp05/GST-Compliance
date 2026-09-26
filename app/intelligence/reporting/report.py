"""
app.intelligence.reporting.report
=================================
IntelligenceReport model compiling Duplicate and Anomaly findings into
a human-readable executive summary and serializable data structures.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.common.enums import (
    AnomalyStatus,
    DuplicateMatchType,
)
from app.intelligence.common.models import IntelligenceFinding
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster


@dataclass
class IntelligenceReport:
    """
    Consolidated Intelligence Report combining Duplicate and Anomaly findings.
    Consumable by UI, CLI, downstream audit workflows, and future AI Agents.
    """
    report_id: str = field(default_factory=lambda: f"INTEL-{uuid.uuid4().hex[:8].upper()}")
    invoices_analyzed: int = 0
    duplicate_clusters: List[DuplicateCluster] = field(default_factory=list)
    duplicate_candidates: List[DuplicateCandidate] = field(default_factory=list)
    anomaly_findings: List[AnomalyFinding] = field(default_factory=list)
    all_findings: List[IntelligenceFinding] = field(default_factory=list)

    # Computed metrics
    exact_duplicate_count: int = 0
    near_duplicate_count: int = 0
    possible_duplicate_count: int = 0
    anomalous_count: int = 0
    insufficient_baseline_count: int = 0
    normal_count: int = 0
    top_findings: List[IntelligenceFinding] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.exact_duplicate_count and self.duplicate_candidates:
            self.exact_duplicate_count = sum(
                1 for c in self.duplicate_candidates if c.match_type == DuplicateMatchType.EXACT_DUPLICATE
            )
        if not self.near_duplicate_count and self.duplicate_candidates:
            self.near_duplicate_count = sum(
                1 for c in self.duplicate_candidates if c.match_type == DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE
            )
        if not self.possible_duplicate_count and self.duplicate_candidates:
            self.possible_duplicate_count = sum(
                1 for c in self.duplicate_candidates if c.match_type == DuplicateMatchType.POSSIBLE_DUPLICATE
            )

        if not self.anomalous_count and self.anomaly_findings:
            # Count unique invoices with at least one anomalous finding
            anom_invs = {af.invoice_id for af in self.anomaly_findings if af.status == AnomalyStatus.ANOMALOUS}
            self.anomalous_count = len(anom_invs)
        if not self.insufficient_baseline_count and self.anomaly_findings:
            insuf_invs = {af.invoice_id for af in self.anomaly_findings if af.status == AnomalyStatus.INSUFFICIENT_BASELINE}
            self.insufficient_baseline_count = len(insuf_invs)
        if not self.normal_count and self.anomaly_findings:
            norm_invs = {af.invoice_id for af in self.anomaly_findings if af.status == AnomalyStatus.NORMAL}
            self.normal_count = len(norm_invs)

        if not self.top_findings and self.all_findings:
            # Rank findings deterministically by score DESC, invoice_id ASC
            sorted_f = sorted(self.all_findings, key=lambda f: (-f.score, f.invoice_id, f.finding_id))
            self.top_findings = sorted_f[:5]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "invoices_analyzed": self.invoices_analyzed,
            "duplicate_summary": {
                "exact_duplicates": self.exact_duplicate_count,
                "high_confidence_near_duplicates": self.near_duplicate_count,
                "possible_duplicates": self.possible_duplicate_count,
                "consolidated_clusters": len(self.duplicate_clusters),
            },
            "anomaly_summary": {
                "anomalous_invoices": self.anomalous_count,
                "insufficient_baseline_invoices": self.insufficient_baseline_count,
                "normal_invoices": self.normal_count,
            },
            "top_findings": [f.to_dict() for f in self.top_findings],
            "duplicate_clusters": [c.to_dict() for c in self.duplicate_clusters],
            "total_findings_count": len(self.all_findings),
        }

    def to_text_summary(self) -> str:
        """Render a clean, auditor-friendly text summary."""
        lines = [
            "=" * 65,
            "  UC15 GST Intelligence Summary",
            "=" * 65,
            f"Report ID            : {self.report_id}",
            f"Invoices Analyzed    : {self.invoices_analyzed:,}",
            "",
            "Duplicate Intelligence:",
            f"  Exact Duplicate Pairs          : {self.exact_duplicate_count:,}",
            f"  High-Confidence Near Duplicates: {self.near_duplicate_count:,}",
            f"  Possible Duplicates            : {self.possible_duplicate_count:,}",
            f"  Consolidated Clusters          : {len(self.duplicate_clusters):,}",
            "",
            "Anomaly Intelligence:",
            f"  Anomalous Invoices             : {self.anomalous_count:,}",
            f"  Insufficient Baseline Invoices : {self.insufficient_baseline_count:,}",
            f"  Normal Invoices                : {self.normal_count:,}",
            "-" * 65,
            "Top Intelligence Findings:",
        ]

        if self.top_findings:
            for idx, f in enumerate(self.top_findings[:5], 1):
                related_str = f" (Related: {', '.join(f.related_invoice_ids)})" if f.related_invoice_ids else ""
                lines.append(
                    f"  {idx}. {f.invoice_id}{related_str}"
                )
                lines.append(
                    f"     Type: {f.finding_type} | Severity: {f.severity} | Score: {f.score:.1f}%"
                )
                if f.description:
                    lines.append(f"     Note: {f.description}")
        else:
            lines.append("  No anomalous or duplicate findings detected.")

        lines.append("=" * 65)
        return "\n".join(lines)
