"""
app.investigation.root_cause.scorer
===================================
Deterministic multi-dimensional scoring engine and causality-safe statement generator.
Computes RootCauseScore, RootCauseConfidence, and RootCauseLikelihood.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

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
from app.investigation.models import RootCauseEvidence, RootCauseScore


CAUSALITY_SAFE_TEMPLATES = {
    RootCauseType.MASTER_DATA: (
        "The observed compliance discrepancies are consistent with a Master Data configuration issue, "
        "specifically regarding GSTIN registration, state identifier mapping, or counterparty profile integrity."
    ),
    RootCauseType.TAX_RATE_CONFIGURATION: (
        "The observed tax variance is consistent with a Tax Rate configuration discrepancy, "
        "where statutory HSN tax schedules differ from rates recorded in ERP billing line items."
    ),
    RootCauseType.PLACE_OF_SUPPLY: (
        "Discrepancies indicate a potential Place of Supply classification mismatch, "
        "manifesting as intra-state versus inter-state tax allocation divergence."
    ),
    RootCauseType.ITC_PROCESS: (
        "The pattern indicates an Input Tax Credit (ITC) process vulnerability, "
        "consistent with GSTR-2B non-reflection or statutory blocked credit criteria under Section 17(5)."
    ),
    RootCauseType.EWB_PROCESS: (
        "Findings are consistent with an E-Way Bill process breakdown, "
        "where consignment thresholds were met without corresponding active electronic transit documentation."
    ),
    RootCauseType.DUPLICATE_PROCESS: (
        "Evidence indicates a potential Duplicate Processing anomaly, "
        "consistent with ERP batch re-upload, document identifier variance, or overlapping invoice submission."
    ),
    RootCauseType.DATA_QUALITY: (
        "Evidence indicates a foundational Data Quality anomaly, "
        "characterized by missing mandatory attributes, malformed date structures, or syntax divergence."
    ),
    RootCauseType.HSN_CLASSIFICATION: (
        "The observed pattern is consistent with an HSN Classification discrepancy, "
        "where item descriptions or commodity codes do not align with statutory tariff schedules."
    ),
    RootCauseType.INTEGRATION_SYNC: (
        "Findings suggest an Integration Synchronization lag between upstream ERP billing "
        "and GST Portal / GSTR-2B settlement systems."
    ),
    RootCauseType.PROCESS_TIMING: (
        "The pattern is consistent with a Process Timing variance across adjacent tax reporting periods."
    ),
    RootCauseType.GSTIN_CONFIGURATION: (
        "Discrepancies are consistent with a GSTIN Configuration syntax or checksum validation issue."
    ),
    RootCauseType.TAX_CONFIGURATION: (
        "The pattern is consistent with a generalized Tax Engine configuration discrepancy."
    ),
    RootCauseType.REFERENCE_DATA: (
        "Discrepancies are consistent with an outdated or unaligned statutory Reference Catalog."
    ),
    RootCauseType.INVOICE_CAPTURE: (
        "Findings suggest an Invoice Capture or transcription variance during ingestion."
    ),
    RootCauseType.UNKNOWN: (
        "Compliance discrepancies observed; however, evidence remains insufficient to establish "
        "a specific systemic root cause hypothesis."
    ),
}


class RootCauseScorer:
    """
    Evaluates candidate evidence deterministically across 6 independent dimensions.
    Enforces causality safety and strict threshold gates.
    """

    def __init__(self, config: Optional[InvestigationConfig] = None) -> None:
        self.config = config or default_investigation_config
        self.policy = self.config.root_cause

    def compute_score(
        self,
        evidence_list: List[RootCauseEvidence],
        affected_count: int,
        total_failed_count: int,
        duration_months: int,
        counterparty_share: float,
        rule_share: float,
    ) -> RootCauseScore:
        """
        Compute normalized 0-100 score across 6 deterministic dimensions.
        """
        w = self.policy.weights

        # 1. Evidence Strength (Max 30.0)
        # Sum weighted independent evidence types
        distinct_types: Set[EvidenceType] = {e.evidence_type for e in evidence_list}
        type_weight_factor = min(len(distinct_types) / 3.0, 1.0)
        raw_evidence_strength = sum(e.weight for e in evidence_list) * 6.0 * type_weight_factor
        evidence_strength = min(w.evidence_strength, max(0.0, raw_evidence_strength))

        # 2. Pattern Recurrence (Max 20.0)
        if affected_count <= 0:
            pattern_recurrence = 0.0
        elif affected_count == 1:
            pattern_recurrence = 5.0
        elif affected_count < 5:
            pattern_recurrence = 10.0
        elif affected_count < 10:
            pattern_recurrence = 15.0
        else:
            pattern_recurrence = w.pattern_recurrence

        # 3. Population Coverage (Max 20.0)
        coverage_ratio = affected_count / total_failed_count if total_failed_count > 0 else 0.0
        population_coverage = min(w.population_coverage, max(0.0, coverage_ratio * w.population_coverage))

        # 4. Temporal Consistency (Max 10.0)
        if duration_months <= 1:
            temporal_consistency = 3.0
        elif duration_months == 2:
            temporal_consistency = 6.5
        else:
            temporal_consistency = w.temporal_consistency

        # 5. Counterparty Concentration (Max 10.0)
        counterparty_concentration = min(w.counterparty_concentration, max(0.0, counterparty_share * w.counterparty_concentration))

        # 6. Rule Concentration (Max 10.0)
        rule_concentration = min(w.rule_concentration, max(0.0, rule_share * w.rule_concentration))

        total_score = min(
            100.0,
            evidence_strength
            + pattern_recurrence
            + population_coverage
            + temporal_consistency
            + counterparty_concentration
            + rule_concentration,
        )

        return RootCauseScore(
            evidence_strength=evidence_strength,
            pattern_recurrence=pattern_recurrence,
            population_coverage=population_coverage,
            temporal_consistency=temporal_consistency,
            counterparty_concentration=counterparty_concentration,
            rule_concentration=rule_concentration,
            total_score=total_score,
        )

    def evaluate_confidence(
        self,
        score: RootCauseScore,
        evidence_list: List[RootCauseEvidence],
        affected_count: int,
    ) -> RootCauseConfidence:
        """Evaluate deterministic confidence level."""
        thresholds = self.policy.confidence_thresholds

        # Safety gate: minimum population required
        if affected_count < thresholds.min_population_size:
            return RootCauseConfidence.INSUFFICIENT_EVIDENCE

        distinct_evidence_types = len({e.evidence_type for e in evidence_list})

        if score.total_score >= thresholds.high and distinct_evidence_types >= thresholds.min_independent_sources_for_high:
            return RootCauseConfidence.HIGH
        elif score.total_score >= thresholds.medium:
            return RootCauseConfidence.MEDIUM
        elif score.total_score >= thresholds.low:
            return RootCauseConfidence.LOW
        else:
            return RootCauseConfidence.INSUFFICIENT_EVIDENCE

    def evaluate_likelihood(self, score: RootCauseScore) -> RootCauseLikelihood:
        """Evaluate deterministic likelihood category."""
        th = self.policy.likelihood_thresholds
        if score.total_score >= th.high:
            return RootCauseLikelihood.HIGH
        elif score.total_score >= th.medium:
            return RootCauseLikelihood.MEDIUM
        else:
            return RootCauseLikelihood.LOW

    def get_causality_statement(self, cause_type: RootCauseType, extra_context: str = "") -> str:
        """Generate causality-safe explanation adhering strictly to enterprise audit standards."""
        base = CAUSALITY_SAFE_TEMPLATES.get(cause_type, CAUSALITY_SAFE_TEMPLATES[RootCauseType.UNKNOWN])
        if extra_context:
            return f"{base} Supporting observations: {extra_context}."
        return base
