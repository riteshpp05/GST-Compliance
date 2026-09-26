"""
app.investigation.evidence.collector
===================================
Orchestrator for extracting, indexing, and structuring evidence from across UC15 modules:
Rule Engine, Decision Engine, Risk Engine (S3), Historical (S5), Financial (S6), Duplicate & Anomaly (S7).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.models.impact import FinancialImpact
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.investigation.enums import EvidenceType
from app.investigation.evidence.models import EvidenceContext
from app.investigation.models import RootCauseEvidence


def extract_period(d_val: Any) -> str:
    """Extract standard YYYY-MM period from date object or ISO string."""
    if hasattr(d_val, "strftime"):
        return d_val.strftime("%Y-%m")
    s = str(d_val or "").strip()
    if len(s) >= 7 and s[4] == "-":
        return s[:7]
    if len(s) >= 10 and s[2] == "-" and s[5] == "-":
        # DD-MM-YYYY format
        return f"{s[6:10]}-{s[3:5]}"
    return "UNKNOWN_PERIOD"


class EvidenceCollector:
    """
    Constructs high-performance indices over all multi-module intelligence signals.
    Emits verified RootCauseEvidence objects with deterministic weights and metrics.
    """

    def collect_context(
        self,
        invoices: List[Invoice],
        decisions: Optional[List[ComplianceDecision]] = None,
        financial_impacts: Optional[List[FinancialImpact]] = None,
        duplicate_candidates: Optional[List[DuplicateCandidate]] = None,
        duplicate_clusters: Optional[List[DuplicateCluster]] = None,
        anomaly_findings: Optional[List[AnomalyFinding]] = None,
        historical_patterns: Optional[List[Any]] = None,
        historical_trends: Optional[List[Any]] = None,
        risk_assessments: Optional[Dict[str, Any]] = None,
    ) -> EvidenceContext:
        """Build indexed EvidenceContext from available cross-engine inputs."""
        ctx = EvidenceContext(total_invoices=len(invoices), invoices=invoices)

        for inv in invoices:
            ctx.invoice_map[inv.invoice_id] = inv
            # Counterparty
            cp_id = inv.counterparty_gstin or inv.gstin or inv.counterparty_name
            ctx.counterparty_names[cp_id] = inv.counterparty_name
            if cp_id not in ctx.invoices_by_counterparty:
                ctx.invoices_by_counterparty[cp_id] = set()
            ctx.invoices_by_counterparty[cp_id].add(inv.invoice_id)

            # Period
            period = extract_period(inv.invoice_date)
            if period not in ctx.invoices_by_period:
                ctx.invoices_by_period[period] = set()
            ctx.invoices_by_period[period].add(inv.invoice_id)

            # HSN
            hsn = inv.hsn_sac or getattr(inv, "hsn_code", "")
            if hsn:
                if hsn not in ctx.invoices_by_hsn:
                    ctx.invoices_by_hsn[hsn] = set()
                ctx.invoices_by_hsn[hsn].add(inv.invoice_id)

            # State / POS
            state = inv.place_of_supply or getattr(inv, "buyer_state", "") or getattr(inv, "seller_state", "")
            if state:
                if state not in ctx.invoices_by_state:
                    ctx.invoices_by_state[state] = set()
                ctx.invoices_by_state[state].add(inv.invoice_id)

        # Index decisions and failed gates
        if decisions:
            ctx.decisions = decisions
            for d in decisions:
                inv_id = getattr(d, "invoice_id", None) or getattr(d, "invoice_no", None)
                if not inv_id:
                    continue
                ctx.decision_map[inv_id] = d

                # Failed or review gates
                failed_gates: List[ValidationResult] = []
                for g in getattr(d, "gates", []):
                    if g.status in ("FAIL", "FAILED", "NON_COMPLIANT"):
                        failed_gates.append(g)
                        rule_key = g.rule_id or g.name
                        if rule_key not in ctx.failed_invoices_by_rule:
                            ctx.failed_invoices_by_rule[rule_key] = set()
                            ctx.rule_failure_details[rule_key] = []
                        ctx.failed_invoices_by_rule[rule_key].add(inv_id)
                        ctx.rule_failure_details[rule_key].append(g)

                        if g.gate_no:
                            if g.gate_no not in ctx.failed_invoices_by_gate_no:
                                ctx.failed_invoices_by_gate_no[g.gate_no] = set()
                            ctx.failed_invoices_by_gate_no[g.gate_no].add(inv_id)

                if failed_gates or d.status in ("NON_COMPLIANT", "NEEDS_REVIEW"):
                    ctx.failed_invoices.add(inv_id)
                    cp_id = d.counterparty_gstin or d.counterparty_name
                    if cp_id:
                        if cp_id not in ctx.failed_invoices_by_counterparty:
                            ctx.failed_invoices_by_counterparty[cp_id] = set()
                        ctx.failed_invoices_by_counterparty[cp_id].add(inv_id)

                    period = extract_period(d.invoice_date)
                    if period:
                        if period not in ctx.failed_invoices_by_period:
                            ctx.failed_invoices_by_period[period] = set()
                        ctx.failed_invoices_by_period[period].add(inv_id)

                    hsn = getattr(d, "hsn_code", "")
                    if hsn:
                        if hsn not in ctx.failed_invoices_by_hsn:
                            ctx.failed_invoices_by_hsn[hsn] = set()
                        ctx.failed_invoices_by_hsn[hsn].add(inv_id)

                    pos = getattr(d, "place_of_supply", "")
                    if pos:
                        if pos not in ctx.failed_invoices_by_state:
                            ctx.failed_invoices_by_state[pos] = set()
                        ctx.failed_invoices_by_state[pos].add(inv_id)

        # Index financial impacts
        if financial_impacts:
            for fi in financial_impacts:
                ctx.financial_impacts_map[fi.invoice_id] = fi

        # Index duplicates
        if duplicate_candidates:
            ctx.all_duplicate_candidates = duplicate_candidates
            for cand in duplicate_candidates:
                inv1 = getattr(cand, "source_invoice_id", None) or getattr(cand, "invoice1_id", None)
                inv2 = getattr(cand, "matched_invoice_id", None) or getattr(cand, "invoice2_id", None)
                if inv1:
                    ctx.duplicates_map.setdefault(inv1, []).append(cand)
                if inv2:
                    ctx.duplicates_map.setdefault(inv2, []).append(cand)
        if duplicate_clusters:
            ctx.duplicate_clusters = duplicate_clusters

        # Index anomalies
        if anomaly_findings:
            ctx.all_anomaly_findings = anomaly_findings
            for anom in anomaly_findings:
                ctx.anomalies_map.setdefault(anom.invoice_id, []).append(anom)

        # Historical & Risk
        if historical_patterns:
            ctx.historical_patterns = historical_patterns
        if historical_trends:
            ctx.historical_trends = historical_trends
        if risk_assessments:
            ctx.risk_assessments = risk_assessments

        return ctx

    @staticmethod
    def build_rule_evidence(
        rule_id: str,
        affected_invoice_ids: List[str],
        gate_no: Optional[int] = None,
        description: str = "",
        details: Optional[List[str]] = None,
    ) -> RootCauseEvidence:
        """Create structured RootCauseEvidence for repeated rule failure."""
        gate_str = f"Gate {gate_no} / " if gate_no else ""
        title = f"Repeated Rule Failure: {gate_str}{rule_id}"
        desc = description or f"Rule {rule_id} failed across {len(affected_invoice_ids)} transaction(s)."
        metrics: Dict[str, Any] = {
            "rule_id": rule_id,
            "gate_no": gate_no,
            "affected_count": len(affected_invoice_ids),
        }
        if details:
            metrics["sample_details"] = details[:5]
        return RootCauseEvidence(
            evidence_id=f"EVID-RULE-{rule_id}",
            evidence_type=EvidenceType.RULE_FAILURE_PATTERN,
            title=title,
            description=desc,
            metrics=metrics,
            affected_count=len(affected_invoice_ids),
            source_ids=affected_invoice_ids,
            weight=1.0,
        )

    @staticmethod
    def build_counterparty_evidence(
        counterparty_id: str,
        counterparty_name: str,
        affected_count: int,
        total_for_counterparty: int,
        concentration_share: float,
        affected_invoice_ids: List[str],
    ) -> RootCauseEvidence:
        """Create structured RootCauseEvidence for counterparty concentration."""
        title = f"Counterparty Discrepancy Concentration: {counterparty_name or counterparty_id}"
        desc = (
            f"{affected_count} of {total_for_counterparty} transaction(s) "
            f"({concentration_share * 100:.1f}%) for counterparty {counterparty_id} show compliance discrepancies."
        )
        return RootCauseEvidence(
            evidence_id=f"EVID-CP-{counterparty_id}",
            evidence_type=EvidenceType.COUNTERPARTY_PATTERN,
            title=title,
            description=desc,
            metrics={
                "counterparty_id": counterparty_id,
                "counterparty_name": counterparty_name,
                "affected_count": affected_count,
                "total_counterparty_invoices": total_for_counterparty,
                "concentration_share": concentration_share,
            },
            affected_count=affected_count,
            source_ids=affected_invoice_ids,
            weight=1.0,
        )

    @staticmethod
    def build_temporal_evidence(
        periods: List[str],
        first_period: str,
        last_period: str,
        affected_count: int,
        affected_invoice_ids: List[str],
    ) -> RootCauseEvidence:
        """Create structured RootCauseEvidence for temporal recurrence."""
        duration = len(periods)
        title = f"Temporal Persistence: Active Across {duration} Tax Period(s)"
        desc = (
            f"Compliance discrepancies persist from {first_period} through {last_period} "
            f"across {duration} distinct period(s)."
        )
        return RootCauseEvidence(
            evidence_id=f"EVID-TEMP-{first_period}-{last_period}",
            evidence_type=EvidenceType.TEMPORAL_PATTERN,
            title=title,
            description=desc,
            metrics={
                "periods": sorted(periods),
                "first_period": first_period,
                "last_period": last_period,
                "duration_months": duration,
                "affected_count": affected_count,
            },
            affected_count=affected_count,
            source_ids=affected_invoice_ids,
            weight=0.8,
        )

    @staticmethod
    def build_financial_evidence(
        total_exposure: Decimal,
        affected_count: int,
        exposure_type: str,
        affected_invoice_ids: List[str],
    ) -> RootCauseEvidence:
        """Create structured RootCauseEvidence for monetary impact concentration."""
        title = f"Quantified Financial Exposure: INR {total_exposure:,.2f}"
        desc = (
            f"Discrepant population carries a verified potential exposure of INR {total_exposure:,.2f} "
            f"primarily driven by {exposure_type}."
        )
        return RootCauseEvidence(
            evidence_id=f"EVID-FIN-{exposure_type}",
            evidence_type=EvidenceType.FINANCIAL_PATTERN,
            title=title,
            description=desc,
            metrics={
                "total_exposure_inr": float(total_exposure),
                "exposure_type": exposure_type,
                "affected_count": affected_count,
            },
            affected_count=affected_count,
            source_ids=affected_invoice_ids,
            weight=0.9,
        )

    @staticmethod
    def build_duplicate_evidence(
        cluster_count: int,
        candidate_count: int,
        affected_invoice_ids: List[str],
    ) -> RootCauseEvidence:
        """Create structured RootCauseEvidence for duplicate process pattern."""
        title = f"Duplicate Invoice Signal: {candidate_count} Candidates / {cluster_count} Clusters"
        desc = (
            f"{candidate_count} duplicate candidate pairs identified across {len(affected_invoice_ids)} "
            f"invoices, indicating potential ERP re-upload or batch ingestion anomalies."
        )
        return RootCauseEvidence(
            evidence_id="EVID-DUP-PROCESS",
            evidence_type=EvidenceType.DUPLICATE_PATTERN,
            title=title,
            description=desc,
            metrics={
                "candidate_count": candidate_count,
                "cluster_count": cluster_count,
                "affected_count": len(affected_invoice_ids),
            },
            affected_count=len(affected_invoice_ids),
            source_ids=affected_invoice_ids,
            weight=1.0,
        )

    @staticmethod
    def build_anomaly_evidence(
        anomaly_count: int,
        dimensions: List[str],
        affected_invoice_ids: List[str],
    ) -> RootCauseEvidence:
        """Create structured RootCauseEvidence for statistical anomaly pattern."""
        title = f"Statistical Anomalies Detected: {anomaly_count} Outliers"
        desc = (
            f"{anomaly_count} statistical outlier(s) detected across {', '.join(dimensions)} "
            f"in the affected population."
        )
        return RootCauseEvidence(
            evidence_id="EVID-ANOM-PATTERN",
            evidence_type=EvidenceType.ANOMALY_PATTERN,
            title=title,
            description=desc,
            metrics={
                "anomaly_count": anomaly_count,
                "dimensions": dimensions,
                "affected_count": len(affected_invoice_ids),
            },
            affected_count=len(affected_invoice_ids),
            source_ids=affected_invoice_ids,
            weight=0.8,
        )
