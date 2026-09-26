"""
app.investigation.root_cause.candidates
=======================================
Deterministic candidate generation engine.
Transforms cross-engine signals into structured, scored RootCauseFinding candidates.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from app.investigation.config.investigation_config import (
    InvestigationConfig,
    default_investigation_config,
)
from app.investigation.enums import (
    EvidenceType,
    RootCauseConfidence,
    RootCauseLikelihood,
    RootCauseStatus,
    RootCauseType,
)
from app.investigation.evidence.collector import EvidenceCollector
from app.investigation.evidence.models import EvidenceContext
from app.investigation.models import RootCauseEvidence, RootCauseFinding, RootCauseScore
from app.investigation.root_cause.patterns import (
    analyze_counterparty_patterns,
    analyze_hsn_patterns,
    analyze_rule_patterns,
    analyze_state_patterns,
    analyze_temporal_patterns,
    get_financial_exposure_for_population,
)
from app.investigation.root_cause.scorer import RootCauseScorer


class CandidateGenerator:
    """
    Evaluates evidence patterns against domain hypotheses to generate root cause candidates.
    Every candidate is backed by concrete evidence items, scored, and causality-checked.
    """

    def __init__(
        self,
        config: Optional[InvestigationConfig] = None,
        scorer: Optional[RootCauseScorer] = None,
    ) -> None:
        self.config = config or default_investigation_config
        self.scorer = scorer or RootCauseScorer(config=self.config)
        self.collector = EvidenceCollector()

    def generate_candidates(self, ctx: EvidenceContext) -> List[RootCauseFinding]:
        """
        Generate and score all viable root cause candidates from the evidence context.
        """
        candidates: List[RootCauseFinding] = []
        total_failed = len(ctx.failed_invoices)
        total_portfolio = ctx.total_invoices

        # -----------------------------------------------------------------
        # 1. Master Data Configuration Candidate (Gate 1 / GSTIN issues)
        # -----------------------------------------------------------------
        g1_invoices = ctx.failed_invoices_by_gate_no.get(1, set())
        for rule_id, invs in ctx.failed_invoices_by_rule.items():
            if "GSTIN" in rule_id.upper() or "R1" in rule_id.upper():
                g1_invoices = g1_invoices.union(invs)

        if g1_invoices:
            c = self._build_candidate(
                ctx=ctx,
                cause_type=RootCauseType.MASTER_DATA,
                affected_invoices=g1_invoices,
                primary_rule_id="R1_GSTIN_STRUCTURE",
                gate_no=1,
                title="Master Data: Counterparty GSTIN Configuration",
            )
            if c:
                candidates.append(c)

        # -----------------------------------------------------------------
        # 2. Tax Rate Configuration Candidate (Gate 3 / Rate Mismatches)
        # -----------------------------------------------------------------
        g3_invoices = ctx.failed_invoices_by_gate_no.get(3, set())
        for rule_id, invs in ctx.failed_invoices_by_rule.items():
            if "TAX_RATE" in rule_id.upper() or "R3" in rule_id.upper():
                g3_invoices = g3_invoices.union(invs)

        if g3_invoices:
            c = self._build_candidate(
                ctx=ctx,
                cause_type=RootCauseType.TAX_RATE_CONFIGURATION,
                affected_invoices=g3_invoices,
                primary_rule_id="R3_TAX_RATE",
                gate_no=3,
                title="Tax Configuration: Statutory Tax Rate Mismatch",
            )
            if c:
                candidates.append(c)

        # -----------------------------------------------------------------
        # 3. Place of Supply Candidate (Gate 4 / State Tax Allocation)
        # -----------------------------------------------------------------
        g4_invoices = ctx.failed_invoices_by_gate_no.get(4, set())
        for rule_id, invs in ctx.failed_invoices_by_rule.items():
            if "PLACE_OF_SUPPLY" in rule_id.upper() or "POS" in rule_id.upper() or "R4" in rule_id.upper():
                g4_invoices = g4_invoices.union(invs)

        if g4_invoices:
            c = self._build_candidate(
                ctx=ctx,
                cause_type=RootCauseType.PLACE_OF_SUPPLY,
                affected_invoices=g4_invoices,
                primary_rule_id="R4_PLACE_OF_SUPPLY",
                gate_no=4,
                title="Place of Supply: Intra vs Inter-State Tax Mismatch",
            )
            if c:
                candidates.append(c)

        # -----------------------------------------------------------------
        # 4. ITC Process Candidate (Gate 6 / Input Tax Credit Eligibility)
        # -----------------------------------------------------------------
        g6_invoices = ctx.failed_invoices_by_gate_no.get(6, set())
        for rule_id, invs in ctx.failed_invoices_by_rule.items():
            if "ITC" in rule_id.upper() or "R6" in rule_id.upper():
                g6_invoices = g6_invoices.union(invs)

        if g6_invoices:
            c = self._build_candidate(
                ctx=ctx,
                cause_type=RootCauseType.ITC_PROCESS,
                affected_invoices=g6_invoices,
                primary_rule_id="R6_ITC_ELIGIBILITY",
                gate_no=6,
                title="ITC Process: Ineligible Credit or Vendor Non-Filing",
            )
            if c:
                candidates.append(c)

        # -----------------------------------------------------------------
        # 5. E-Way Bill Process Candidate (Gate 5 / Transit Documentation)
        # -----------------------------------------------------------------
        g5_invoices = ctx.failed_invoices_by_gate_no.get(5, set())
        for rule_id, invs in ctx.failed_invoices_by_rule.items():
            if "EWAY" in rule_id.upper() or "EWB" in rule_id.upper() or "R5" in rule_id.upper():
                g5_invoices = g5_invoices.union(invs)

        if g5_invoices:
            c = self._build_candidate(
                ctx=ctx,
                cause_type=RootCauseType.EWB_PROCESS,
                affected_invoices=g5_invoices,
                primary_rule_id="R5_EWAY_BILL",
                gate_no=5,
                title="E-Way Bill: Missing Transit Documentation Over Threshold",
            )
            if c:
                candidates.append(c)

        # -----------------------------------------------------------------
        # 6. Duplicate Process Candidate (Sprint 7 Signals)
        # -----------------------------------------------------------------
        dup_invoices: Set[str] = set()
        for cl in ctx.duplicate_clusters:
            dup_invoices.update(cl.invoice_ids)
        for cand in ctx.all_duplicate_candidates:
            m_type = cand.match_type.value if hasattr(cand.match_type, "value") else str(cand.match_type)
            if m_type != "NO_DUPLICATE":
                inv1 = getattr(cand, "source_invoice_id", None) or getattr(cand, "invoice1_id", None)
                inv2 = getattr(cand, "matched_invoice_id", None) or getattr(cand, "invoice2_id", None)
                if inv1:
                    dup_invoices.add(inv1)
                if inv2:
                    dup_invoices.add(inv2)

        if dup_invoices:
            c = self._build_duplicate_candidate(ctx, dup_invoices)
            if c:
                candidates.append(c)

        # -----------------------------------------------------------------
        # 7. HSN Classification Candidate (Gate 2 / Tariff Code Lookup)
        # -----------------------------------------------------------------
        g2_invoices = ctx.failed_invoices_by_gate_no.get(2, set())
        for rule_id, invs in ctx.failed_invoices_by_rule.items():
            if "HSN" in rule_id.upper() or "R2" in rule_id.upper():
                g2_invoices = g2_invoices.union(invs)

        if g2_invoices:
            c = self._build_candidate(
                ctx=ctx,
                cause_type=RootCauseType.HSN_CLASSIFICATION,
                affected_invoices=g2_invoices,
                primary_rule_id="R2_HSN_LOOKUP",
                gate_no=2,
                title="HSN Classification: Unmapped Tariff Code or Description",
            )
            if c:
                candidates.append(c)

        # -----------------------------------------------------------------
        # 8. Handling when no candidates or only insufficient evidence exists
        # -----------------------------------------------------------------
        if not candidates and ctx.failed_invoices:
            # Fallback candidate with INSUFFICIENT_EVIDENCE
            c = self._build_unknown_candidate(ctx, ctx.failed_invoices)
            if c:
                candidates.append(c)

        return candidates

    def _build_candidate(
        self,
        ctx: EvidenceContext,
        cause_type: RootCauseType,
        affected_invoices: Set[str],
        primary_rule_id: str,
        gate_no: int,
        title: str,
    ) -> Optional[RootCauseFinding]:
        if not affected_invoices:
            return None

        evidence_list: List[RootCauseEvidence] = []
        aff_list = sorted(affected_invoices)

        # 1. Rule Failure Evidence
        rule_evid = self.collector.build_rule_evidence(
            rule_id=primary_rule_id,
            affected_invoice_ids=aff_list,
            gate_no=gate_no,
        )
        evidence_list.append(rule_evid)

        # 2. Counterparty Analysis
        cp_patterns = analyze_counterparty_patterns(ctx, affected_invoices)
        top_cp_id = None
        top_cp_share = 0.0
        if cp_patterns:
            top_cp_info = max(cp_patterns.values(), key=lambda x: x["share_of_affected"])
            top_cp_id = top_cp_info["counterparty_id"]
            top_cp_share = top_cp_info["share_of_affected"]
            if top_cp_share >= 0.40 or len(cp_patterns) == 1:
                cp_evid = self.collector.build_counterparty_evidence(
                    counterparty_id=top_cp_id,
                    counterparty_name=top_cp_info["counterparty_name"],
                    affected_count=top_cp_info["affected_count"],
                    total_for_counterparty=top_cp_info["total_count"],
                    concentration_share=top_cp_share,
                    affected_invoice_ids=top_cp_info["invoice_ids"],
                )
                evidence_list.append(cp_evid)

        # 3. Temporal Analysis
        temp_info = analyze_temporal_patterns(ctx, affected_invoices)
        duration_months = temp_info["duration_months"]
        if duration_months >= 2:
            temp_evid = self.collector.build_temporal_evidence(
                periods=temp_info["periods"],
                first_period=temp_info["first_period"],
                last_period=temp_info["last_period"],
                affected_count=len(affected_invoices),
                affected_invoice_ids=aff_list,
            )
            evidence_list.append(temp_evid)

        # 4. Financial Exposure Analysis (Reconciled from S6)
        total_exp, exp_by_type = get_financial_exposure_for_population(ctx, affected_invoices)
        if total_exp > Decimal("0.00"):
            primary_exp_type = max(exp_by_type.items(), key=lambda x: x[1])[0] if exp_by_type else "TAX_EXPOSURE"
            fin_evid = self.collector.build_financial_evidence(
                total_exposure=total_exp,
                affected_count=len(affected_invoices),
                exposure_type=primary_exp_type,
                affected_invoice_ids=aff_list,
            )
            evidence_list.append(fin_evid)

        # 5. S7 Overlap (Duplicate & Anomaly)
        dup_overlap = [inv_id for inv_id in aff_list if inv_id in ctx.duplicates_map]
        anom_overlap = [inv_id for inv_id in aff_list if inv_id in ctx.anomalies_map]

        if dup_overlap:
            evidence_list.append(
                RootCauseEvidence(
                    evidence_id="EVID-DUP-OVERLAP",
                    evidence_type=EvidenceType.DUPLICATE_PATTERN,
                    title=f"Duplicate Signal Overlap ({len(dup_overlap)} Invoices)",
                    description=f"{len(dup_overlap)} invoice(s) in this candidate population also exhibit duplicate candidates.",
                    metrics={"duplicate_invoice_count": len(dup_overlap)},
                    affected_count=len(dup_overlap),
                    source_ids=dup_overlap,
                    weight=0.7,
                )
            )

        if anom_overlap:
            evidence_list.append(
                RootCauseEvidence(
                    evidence_id="EVID-ANOM-OVERLAP",
                    evidence_type=EvidenceType.ANOMALY_PATTERN,
                    title=f"Statistical Anomaly Overlap ({len(anom_overlap)} Invoices)",
                    description=f"{len(anom_overlap)} invoice(s) in this population show statistical value/frequency outliers.",
                    metrics={"anomaly_invoice_count": len(anom_overlap)},
                    affected_count=len(anom_overlap),
                    source_ids=anom_overlap,
                    weight=0.7,
                )
            )

        # Compute Score
        total_failed_in_ctx = max(len(ctx.failed_invoices), 1)
        rule_share = len(affected_invoices) / total_failed_in_ctx
        score = self.scorer.compute_score(
            evidence_list=evidence_list,
            affected_count=len(affected_invoices),
            total_failed_count=total_failed_in_ctx,
            duration_months=duration_months,
            counterparty_share=top_cp_share,
            rule_share=rule_share,
        )

        confidence = self.scorer.evaluate_confidence(score, evidence_list, len(affected_invoices))
        likelihood = self.scorer.evaluate_likelihood(score)
        causality_statement = self.scorer.get_causality_statement(
            cause_type,
            extra_context=f"{len(affected_invoices)} invoices affected across {duration_months} period(s)",
        )

        status = RootCauseStatus.ACTIVE
        if confidence == RootCauseConfidence.INSUFFICIENT_EVIDENCE:
            status = RootCauseStatus.INSUFFICIENT_EVIDENCE

        # Supporting entities
        supporting_rules = [primary_rule_id]
        supporting_cps = [top_cp_id] if top_cp_id else []
        supporting_periods = temp_info["periods"]

        return RootCauseFinding(
            root_cause_id=f"RC-{cause_type.value}-{gate_no:02d}",
            root_cause_type=cause_type,
            title=title,
            description=(
                f"{len(affected_invoices)} invoice(s) exhibit recurring discrepancies under Gate {gate_no} ({primary_rule_id}). "
                f"Concentration in primary counterparty: {top_cp_share * 100:.1f}%."
            ),
            status=status,
            confidence=confidence,
            likelihood=likelihood,
            severity="HIGH" if score.total_score >= 70 else ("MEDIUM" if score.total_score >= 40 else "LOW"),
            score=score,
            causality_statement=causality_statement,
            evidence=evidence_list,
            affected_invoice_ids=aff_list,
            supporting_finding_ids=[e.evidence_id for e in evidence_list],
            supporting_rule_ids=supporting_rules,
            supporting_counterparty_ids=supporting_cps,
            supporting_periods=supporting_periods,
            financial_exposure=total_exp,
            detector_version="1.0",
            lineage={
                "candidate_source": "rule_failure_pattern",
                "primary_gate": gate_no,
                "primary_rule": primary_rule_id,
            },
        )

    def _build_duplicate_candidate(
        self,
        ctx: EvidenceContext,
        dup_invoices: Set[str],
    ) -> Optional[RootCauseFinding]:
        aff_list = sorted(dup_invoices)
        evidence_list: List[RootCauseEvidence] = []

        dup_evid = self.collector.build_duplicate_evidence(
            cluster_count=len(ctx.duplicate_clusters),
            candidate_count=len(ctx.all_duplicate_candidates),
            affected_invoice_ids=aff_list,
        )
        evidence_list.append(dup_evid)

        # Counterparty pattern for duplicates
        cp_patterns = analyze_counterparty_patterns(ctx, dup_invoices)
        top_cp_id = None
        top_cp_share = 0.0
        if cp_patterns:
            top_cp_info = max(cp_patterns.values(), key=lambda x: x["share_of_affected"])
            top_cp_id = top_cp_info["counterparty_id"]
            top_cp_share = top_cp_info["share_of_affected"]
            cp_evid = self.collector.build_counterparty_evidence(
                counterparty_id=top_cp_id,
                counterparty_name=top_cp_info["counterparty_name"],
                affected_count=top_cp_info["affected_count"],
                total_for_counterparty=top_cp_info["total_count"],
                concentration_share=top_cp_share,
                affected_invoice_ids=top_cp_info["invoice_ids"],
            )
            evidence_list.append(cp_evid)

        # Financial exposure
        total_exp, _ = get_financial_exposure_for_population(ctx, dup_invoices)
        if total_exp > Decimal("0.00"):
            fin_evid = self.collector.build_financial_evidence(
                total_exposure=total_exp,
                affected_count=len(dup_invoices),
                exposure_type="DUPLICATE_INVOICE_EXPOSURE",
                affected_invoice_ids=aff_list,
            )
            evidence_list.append(fin_evid)

        temp_info = analyze_temporal_patterns(ctx, dup_invoices)
        duration_months = max(temp_info["duration_months"], 1)

        total_failed_in_ctx = max(len(ctx.failed_invoices), len(dup_invoices))
        score = self.scorer.compute_score(
            evidence_list=evidence_list,
            affected_count=len(dup_invoices),
            total_failed_count=total_failed_in_ctx,
            duration_months=duration_months,
            counterparty_share=top_cp_share,
            rule_share=0.8,
        )

        confidence = self.scorer.evaluate_confidence(score, evidence_list, len(dup_invoices))
        likelihood = self.scorer.evaluate_likelihood(score)
        causality_statement = self.scorer.get_causality_statement(
            RootCauseType.DUPLICATE_PROCESS,
            extra_context=f"{len(dup_invoices)} invoices identified in duplicate candidate pairs / clusters",
        )

        return RootCauseFinding(
            root_cause_id="RC-DUPLICATE-PROCESS-01",
            root_cause_type=RootCauseType.DUPLICATE_PROCESS,
            title="Duplicate Process: Redundant Invoices or Batch Re-upload",
            description=(
                f"{len(dup_invoices)} invoice(s) identified in {len(ctx.all_duplicate_candidates)} duplicate candidate pair(s) "
                f"across {len(ctx.duplicate_clusters)} cluster(s)."
            ),
            status=RootCauseStatus.ACTIVE if confidence != RootCauseConfidence.INSUFFICIENT_EVIDENCE else RootCauseStatus.INSUFFICIENT_EVIDENCE,
            confidence=confidence,
            likelihood=likelihood,
            severity="MEDIUM",
            score=score,
            causality_statement=causality_statement,
            evidence=evidence_list,
            affected_invoice_ids=aff_list,
            supporting_finding_ids=[e.evidence_id for e in evidence_list],
            supporting_rule_ids=["DUPLICATE_CHECK"],
            supporting_counterparty_ids=[top_cp_id] if top_cp_id else [],
            supporting_periods=temp_info["periods"],
            financial_exposure=total_exp,
            detector_version="1.0",
            lineage={"candidate_source": "duplicate_intelligence_s7"},
        )

    def _build_unknown_candidate(
        self,
        ctx: EvidenceContext,
        affected_invoices: Set[str],
    ) -> Optional[RootCauseFinding]:
        aff_list = sorted(affected_invoices)
        evidence_list: List[RootCauseEvidence] = [
            RootCauseEvidence(
                evidence_id="EVID-UNCLASSIFIED",
                evidence_type=EvidenceType.RULE_FAILURE_PATTERN,
                title="Unclassified Compliance Discrepancy",
                description=f"{len(aff_list)} invoice(s) failed compliance validation without matching a dominant systemic pattern.",
                metrics={"affected_count": len(aff_list)},
                affected_count=len(aff_list),
                source_ids=aff_list,
                weight=0.5,
            )
        ]

        total_exp, _ = get_financial_exposure_for_population(ctx, affected_invoices)
        score = RootCauseScore(
            evidence_strength=5.0,
            pattern_recurrence=5.0,
            population_coverage=5.0,
            temporal_consistency=2.0,
            counterparty_concentration=2.0,
            rule_concentration=2.0,
            total_score=21.0,
        )

        return RootCauseFinding(
            root_cause_id="RC-UNKNOWN-00",
            root_cause_type=RootCauseType.UNKNOWN,
            title="Insufficient Evidence for Systemic Root Cause",
            description="Available compliance signals are insufficient or heterogeneous to establish a confirmed systemic root cause.",
            status=RootCauseStatus.INSUFFICIENT_EVIDENCE,
            confidence=RootCauseConfidence.INSUFFICIENT_EVIDENCE,
            likelihood=RootCauseLikelihood.LOW,
            severity="LOW",
            score=score,
            causality_statement=self.scorer.get_causality_statement(RootCauseType.UNKNOWN),
            evidence=evidence_list,
            affected_invoice_ids=aff_list,
            supporting_finding_ids=["EVID-UNCLASSIFIED"],
            supporting_rule_ids=[],
            supporting_counterparty_ids=[],
            supporting_periods=[],
            financial_exposure=total_exp,
            detector_version="1.0",
            lineage={"candidate_source": "fallback"},
        )
