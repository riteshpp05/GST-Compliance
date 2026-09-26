"""
app.investigation.investigation_service
=======================================
Central Orchestration Service for Root Cause & Blast Radius Intelligence (Sprint 8 + 9).
Harmonizes cross-engine intelligence (S1-S7) into verifiable, reproducible, and explainable
InvestigationProfiles consumed by human compliance leads and future AI Agents (Sprint 11).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.financial.models.impact import FinancialImpact
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.investigation.blast_radius.engine import BlastRadiusEngine
from app.investigation.config.investigation_config import (
    InvestigationConfig,
    default_investigation_config,
)
from app.investigation.enums import (
    InvestigationStatus,
    RootCauseConfidence,
    RootCauseStatus,
    RootCauseType,
    SystemicClassification,
    TrendClassification,
)
from app.investigation.evidence.collector import EvidenceCollector, extract_period
from app.investigation.evidence.models import EvidenceContext
from app.investigation.models import (
    BlastRadiusProfile,
    InvestigationProfile,
    RootCauseFinding,
)
from app.investigation.repository.base import BaseInvestigationRepository
from app.investigation.repository.in_memory import InMemoryInvestigationRepository
from app.investigation.root_cause.engine import RootCauseEngine


class InvestigationService:
    """
    Main entry point for Root Cause & Blast Radius Intelligence.
    Produces unified InvestigationProfile dossiers.
    """

    def __init__(
        self,
        repository: Optional[BaseInvestigationRepository] = None,
        config: Optional[InvestigationConfig] = None,
        root_cause_engine: Optional[RootCauseEngine] = None,
        blast_radius_engine: Optional[BlastRadiusEngine] = None,
        collector: Optional[EvidenceCollector] = None,
    ) -> None:
        self.repository = repository or InMemoryInvestigationRepository()
        self.config = config or default_investigation_config
        self.root_cause_engine = root_cause_engine or RootCauseEngine(config=self.config)
        self.blast_radius_engine = blast_radius_engine or BlastRadiusEngine(config=self.config)
        self.collector = collector or EvidenceCollector()

    def evaluate_batch(
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
    ) -> InvestigationProfile:
        """
        Execute end-to-end investigation workflow over batch compliance results:
        1. Collect structured evidence context
        2. Derive root cause hypotheses and rank candidates
        3. Quantify multidimensional blast radius and systemic boundaries
        4. Reconcile financial exposures and risk severity
        5. Build deterministic event timeline and evidence trace graph
        6. Formulate actionable recommendations for future AI agent
        """
        # 1. Build Evidence Context
        ctx = self.collector.collect_context(
            invoices=invoices,
            decisions=decisions,
            financial_impacts=financial_impacts,
            duplicate_candidates=duplicate_candidates,
            duplicate_clusters=duplicate_clusters,
            anomaly_findings=anomaly_findings,
            historical_patterns=historical_patterns,
            historical_trends=historical_trends,
            risk_assessments=risk_assessments,
        )

        # 2. Derive Root Causes
        primary_rc, candidates = self.root_cause_engine.analyze(ctx)
        self.repository.add_root_causes(candidates)

        # 3. Calculate Blast Radius
        primary_target_ids: Set[str] = set()
        rc_id = "GLOBAL"
        if primary_rc and primary_rc.affected_invoice_ids:
            primary_target_ids = set(primary_rc.affected_invoice_ids)
            rc_id = primary_rc.root_cause_id
        elif ctx.failed_invoices:
            primary_target_ids = ctx.failed_invoices
            rc_id = "FAILED_POPULATION"

        primary_blast_radius = self.blast_radius_engine.calculate_profile(
            ctx=ctx,
            target_invoice_ids=primary_target_ids,
            root_cause_id=rc_id,
        )
        self.repository.add_blast_radius(primary_blast_radius)

        # Also calculate blast radius for all secondary candidates
        for cand in candidates:
            if cand != primary_rc and cand.affected_invoice_ids:
                cand_br = self.blast_radius_engine.calculate_profile(
                    ctx=ctx,
                    target_invoice_ids=set(cand.affected_invoice_ids),
                    root_cause_id=cand.root_cause_id,
                )
                self.repository.add_blast_radius(cand_br)

        # 4. Generate Timeline
        timeline = self._generate_timeline(ctx, primary_target_ids)

        # 5. Generate Evidence Trace Graph
        evidence_graph = self._generate_evidence_graph(primary_rc, ctx)

        # 6. Formulate AI Agent Investigation Recommendations
        recommended_areas = self._generate_recommendations(primary_rc, primary_blast_radius)

        # Determine Investigation Status
        inv_status = InvestigationStatus.OPEN
        if not candidates or (primary_rc and primary_rc.confidence == RootCauseConfidence.INSUFFICIENT_EVIDENCE):
            inv_status = InvestigationStatus.INSUFFICIENT_EVIDENCE
        elif primary_blast_radius.affected_invoice_count == 0:
            inv_status = InvestigationStatus.COMPLETED

        # 7. Construct Investigation Profile
        profile = InvestigationProfile(
            investigation_id="INV-ROOT-001",
            title="GST Root Cause & Impact Intelligence Dossier",
            status=inv_status,
            primary_root_cause=primary_rc,
            root_cause_candidates=candidates,
            blast_radius=primary_blast_radius,
            financial_exposure=primary_blast_radius.total_potential_exposure,
            exposure_summary={k: float(v) for k, v in primary_blast_radius.exposure_by_type.items()},
            risk_distribution=primary_blast_radius.severity_distribution,
            duplicate_signals_summary={
                "affected_invoice_count": primary_blast_radius.duplicate_affected_count,
                "candidate_ids": primary_blast_radius.duplicate_candidate_ids[:5],
            },
            anomaly_signals_summary={
                "outlier_invoice_count": primary_blast_radius.anomaly_affected_count,
                "finding_ids": primary_blast_radius.anomaly_finding_ids[:5],
            },
            historical_pattern_summary={
                "duration_months": primary_blast_radius.duration_periods,
                "first_detected_period": primary_blast_radius.first_detected_period,
                "last_detected_period": primary_blast_radius.last_detected_period,
            },
            concentration_summary={
                "top_counterparty_id": primary_blast_radius.top_counterparty_id,
                "top_counterparty_share": primary_blast_radius.top_counterparty_share,
                "top_rule_id": primary_blast_radius.top_rule_id,
                "top_rule_share": primary_blast_radius.top_rule_share,
            },
            trend=primary_blast_radius.trend.value,
            systemic_classification=primary_blast_radius.systemic_classification.value,
            timeline=timeline,
            evidence_graph=evidence_graph,
            recommended_investigation_areas=recommended_areas,
            lineage={
                "root_cause_version": "1.0",
                "blast_radius_version": "1.0",
                "investigation_engine": "deterministic_v1.0",
                "candidate_count": len(candidates),
            },
        )

        self.repository.set_investigation_profile(profile)
        return profile

    def get_investigation_profile(self, investigation_id: Optional[str] = None) -> Optional[InvestigationProfile]:
        """Retrieve stored investigation profile."""
        return self.repository.get_investigation_profile(investigation_id)

    def _generate_timeline(
        self,
        ctx: EvidenceContext,
        target_invoice_ids: Set[str],
    ) -> List[Dict[str, Any]]:
        """Generate chronological sequence of observed compliance milestones."""
        if not target_invoice_ids:
            return []

        period_invoices: Dict[str, List[str]] = {}
        for inv_id in target_invoice_ids:
            inv = ctx.invoice_map.get(inv_id)
            if inv:
                p = extract_period(inv.invoice_date)
                period_invoices.setdefault(p, []).append(inv_id)

        sorted_periods = sorted([p for p in period_invoices.keys() if p != "UNKNOWN_PERIOD"])
        timeline: List[Dict[str, Any]] = []

        cumulative_count = 0
        cumulative_exposure = Decimal("0.00")

        for idx, p in enumerate(sorted_periods):
            invs_in_p = period_invoices[p]
            count_in_p = len(invs_in_p)
            cumulative_count += count_in_p

            exp_in_p = Decimal("0.00")
            for i_id in invs_in_p:
                fi = ctx.financial_impacts_map.get(i_id)
                if fi and fi.potential_exposure:
                    exp_in_p += fi.potential_exposure
            cumulative_exposure += exp_in_p

            milestone_type = "INITIAL_DETECTION" if idx == 0 else "PERSISTENCE"
            if idx == len(sorted_periods) - 1 and len(sorted_periods) > 1:
                milestone_type = "LATEST_DETECTION"

            timeline.append({
                "period": p,
                "event_type": milestone_type,
                "period_affected_invoices": count_in_p,
                "cumulative_affected_invoices": cumulative_count,
                "period_exposure": float(exp_in_p),
                "cumulative_exposure": float(cumulative_exposure),
                "sample_invoices": invs_in_p[:3],
            })

        return timeline

    def _generate_evidence_graph(
        self,
        primary_rc: Optional[RootCauseFinding],
        ctx: EvidenceContext,
    ) -> Dict[str, List[str]]:
        """
        Generate traceable adjacency mapping:
        root_cause -> [evidence_ids]
        evidence_id -> [invoice_ids]
        invoice_id -> [counterparty_id, rule_ids, period]
        """
        graph: Dict[str, List[str]] = {}
        if not primary_rc:
            return graph

        rc_node = f"ROOT_CAUSE:{primary_rc.root_cause_id}"
        graph[rc_node] = [f"EVIDENCE:{e.evidence_id}" for e in primary_rc.evidence]

        for e in primary_rc.evidence:
            e_node = f"EVIDENCE:{e.evidence_id}"
            graph[e_node] = [f"INVOICE:{inv_id}" for inv_id in e.source_ids[:10]]

        for inv_id in primary_rc.affected_invoice_ids[:10]:
            inv_node = f"INVOICE:{inv_id}"
            inv = ctx.invoice_map.get(inv_id)
            links = []
            if inv:
                cp_id = inv.counterparty_gstin or inv.counterparty_name
                if cp_id:
                    links.append(f"COUNTERPARTY:{cp_id}")
                links.append(f"PERIOD:{extract_period(inv.invoice_date)}")
            d = ctx.decision_map.get(inv_id)
            if d:
                for g in getattr(d, "gates", []):
                    if g.status in ("FAIL", "FAILED", "NON_COMPLIANT"):
                        links.append(f"RULE:{g.rule_id or g.name}")
            graph[inv_node] = links

        return graph

    def _generate_recommendations(
        self,
        primary_rc: Optional[RootCauseFinding],
        blast_radius: BlastRadiusProfile,
    ) -> List[str]:
        """Formulate next-step investigation areas for future AI agent / compliance analyst."""
        if not primary_rc:
            return ["Review data ingestion pipeline for unparsed transactions or schema anomalies."]

        recs: List[str] = []
        rc_type = primary_rc.root_cause_type
        top_cp = blast_radius.top_counterparty_id or "primary counterparty"
        top_hsn = blast_radius.top_hsn or "affected HSN codes"

        if rc_type == RootCauseType.MASTER_DATA:
            recs.append(f"Audit ERP vendor master records for GSTIN and state code consistency for {top_cp}.")
            recs.append("Verify counterparty active registration status on the GST Common Portal.")
        elif rc_type == RootCauseType.TAX_RATE_CONFIGURATION:
            recs.append(f"Reconcile ERP tax rate condition tables against statutory tariff schedules for {top_hsn}.")
            recs.append("Review whether concessionary GST notifications apply to affected item descriptions.")
        elif rc_type == RootCauseType.PLACE_OF_SUPPLY:
            recs.append("Audit bill-to vs ship-to address master data to correct intra/inter-state tax allocations.")
            recs.append("Confirm statutory Place of Supply rules under Section 10/12 of the IGST Act.")
        elif rc_type == RootCauseType.ITC_PROCESS:
            recs.append(f"Execute GSTR-2B settlement reconciliation with {top_cp} to confirm supplier return filing.")
            recs.append("Review procurement line items against statutory blocked credit exclusions under Section 17(5).")
        elif rc_type == RootCauseType.EWB_PROCESS:
            recs.append("Review e-way bill generation workflows and transporter consignment thresholds (INR 50,000+).")
            recs.append("Verify vehicle number and electronic transit validity dates for in-transit shipments.")
        elif rc_type == RootCauseType.DUPLICATE_PROCESS:
            recs.append("Inspect ERP ingestion batch job logs to identify potential duplicate upload occurrences.")
            recs.append("Verify purchase order number references to isolate potential re-invoicing.")
        else:
            recs.append(f"Examine underlying transaction source documents for {len(blast_radius.affected_invoice_ids)} affected invoices.")

        if blast_radius.duplicate_and_anomaly_overlap_count > 0:
            recs.append(
                f"Prioritize investigation of {blast_radius.duplicate_and_anomaly_overlap_count} transactions "
                "exhibiting compound duplicate and statistical anomaly signals."
            )

        if blast_radius.trend == TrendClassification.EXPANDING:
            recs.append("Initiate immediate containment action: discrepancy trend is expanding across recent tax periods.")

        return recs
