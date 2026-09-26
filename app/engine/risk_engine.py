"""
UC15 GST Compliance Agent — Risk Scoring & Categorization Engine (Sprint 3)
Evaluates compliance validation reports and decisions to compute deterministic,
explainable, and configurable transaction risk scores (0–100), risk levels,
investigation priorities, confidence ratings, and category risk breakdowns.

Separates Compliance Status, Risk Score, Severity, Data Quality, and Financial Exposure.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.config.risk_config import RiskConfig, load_risk_config
from app.domain.enums.compliance_status import ComplianceStatus
from app.domain.enums.confidence_level import ConfidenceLevel
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.risk_priority import RiskPriority
from app.domain.models.invoice import Invoice
from app.domain.models.risk import (
    BatchRiskReport,
    CategoryRisk,
    RiskAssessment,
    RiskDistribution,
    RiskFactor,
)
from app.domain.models.validation import ComplianceDecision, ValidationReport, ValidationResult
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class RiskEngine:
    """
    Deterministic, configurable risk intelligence engine for UC15.
    Interprets compliance findings into business/operational risk without ML, LLMs, or RAG.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or load_risk_config()

    def level_for_score(self, score: float) -> str:
        """Map numeric risk score (0–100) to configured RiskLevel string."""
        score_val = max(0.0, min(100.0, float(score)))
        sorted_levels = sorted(self.config.levels.items(), key=lambda x: x[1].min)
        for i, (name, r) in enumerate(sorted_levels):
            next_min = sorted_levels[i + 1][1].min if i + 1 < len(sorted_levels) else 100.01
            if r.min <= score_val < next_min or (i == len(sorted_levels) - 1 and score_val >= r.min):
                return name
        return RiskLevel.CRITICAL.value

    def priority_for_level(self, level: str, has_critical: bool = False) -> str:
        """Determine investigation priority (P1–P4) based on risk level and critical overrides."""
        if has_critical and self.config.policy.critical_override.enabled:
            return self.config.policy.critical_override.force_priority
        return self.config.policy.priority_mapping.get(level, RiskPriority.P3.value)

    def assess(
        self,
        invoice: Invoice,
        validation_report: ValidationReport,
        compliance_decision: ComplianceDecision,
        context: Optional[Any] = None,
    ) -> RiskAssessment:
        """
        Assess risk for a single invoice based on its validation report and compliance decision.
        """
        statutory_results = [r for r in validation_report.results if r.gate_no is not None]
        data_quality_results = [
            r for r in validation_report.results
            if r.category == "DATA_QUALITY" or r.gate_no is None
        ]

        failed_statutory = [r for r in statutory_results if r.status == "FAIL"]
        warning_statutory = [r for r in statutory_results if r.status == "WARNING"]
        failed_dq = [r for r in data_quality_results if r.status in ("FAIL", "WARNING")]

        # Handle clean invoice with zero findings
        if not failed_statutory and not warning_statutory and not failed_dq:
            assessment = RiskAssessment(
                invoice_id=invoice.invoice_number,
                risk_score=0.0,
                risk_level=RiskLevel.LOW.value,
                priority=RiskPriority.P4.value,
                confidence=ConfidenceLevel.HIGH.value,
                confidence_score=1.0,
                explanation="Low risk (Score: 0.0, Level: LOW, Priority: P4, Confidence: HIGH). "
                            "Clean invoice with zero compliance or data quality findings. Fully filing ready.",
                risk_factors=[],
                contributing_findings=[],
                category_scores={},
                severity_contribution=0.0,
                data_quality_impact=0.0,
                risk_model_version=self.config.policy.model_version,
            )
            compliance_decision.risk_score = 0.0
            compliance_decision.risk_level = RiskLevel.LOW.value
            compliance_decision.priority = RiskPriority.P4.value
            compliance_decision.risk_assessment = assessment
            return assessment

        factors: List[RiskFactor] = []
        contributing_findings: List[str] = []
        category_findings: Dict[str, List[ValidationResult]] = {}

        # 1. Severity Contributions from Statutory Failures
        for r in failed_statutory:
            sev = r.severity or "MEDIUM"
            weight = getattr(self.config.weights.severity, sev, 15.0)
            factors.append(
                RiskFactor(
                    factor_id=f"SEV_{r.rule_id}",
                    name=f"{r.rule_id} Severity ({sev})",
                    description=f"{r.rule_name}: {r.message}",
                    contribution=float(weight),
                    category=r.category,
                    severity=sev,
                    rule_id=r.rule_id,
                    evidence=r.evidence if isinstance(r.evidence, dict) else None,
                )
            )
            contributing_findings.append(r.rule_id)
            category_findings.setdefault(r.category, []).append(r)

        # 2. Severity Contributions from Statutory Warnings
        for r in warning_statutory:
            sev = r.severity or "LOW"
            base_w = getattr(self.config.weights.severity, sev, 5.0)
            weight = base_w * self.config.weights.warning_severity_factor
            factors.append(
                RiskFactor(
                    factor_id=f"SEV_{r.rule_id}_WARN",
                    name=f"{r.rule_id} Warning ({sev})",
                    description=f"Warning from {r.rule_name}: {r.message}",
                    contribution=float(weight),
                    category=r.category,
                    severity=sev,
                    rule_id=r.rule_id,
                    evidence=r.evidence if isinstance(r.evidence, dict) else None,
                )
            )
            contributing_findings.append(r.rule_id)
            category_findings.setdefault(r.category, []).append(r)

        severity_contribution = sum(f.contribution for f in factors)

        # 3. Category Contributions
        for cat, findings in category_findings.items():
            cat_w = getattr(self.config.weights.category, cat, self.config.weights.category.OTHER)
            factors.append(
                RiskFactor(
                    factor_id=f"CAT_{cat}",
                    name=f"{cat} Category Compliance Risk",
                    description=f"Category risk for {cat} containing {len(findings)} finding(s).",
                    contribution=float(cat_w),
                    category=cat,
                )
            )

        # 4. Multiple Findings Compounding Penalty
        if len(failed_statutory) > 1:
            extra = len(failed_statutory) - 1
            mult_penalty = min(
                self.config.weights.max_multiple_findings_penalty,
                extra * self.config.weights.multiple_findings_penalty,
            )
            factors.append(
                RiskFactor(
                    factor_id="MULTIPLE_FINDINGS",
                    name="Multiple Statutory Failures Compounding",
                    description=f"Compounding compliance risk for {len(failed_statutory)} concurrent statutory failures.",
                    contribution=float(mult_penalty),
                    category="COMPLIANCE",
                )
            )

        # 5. Data Quality Contributions
        dq_penalty = 0.0
        for dq in failed_dq:
            dq_w = self.config.weights.data_quality_penalty
            if dq_penalty + dq_w <= self.config.weights.max_data_quality_penalty:
                dq_penalty += dq_w
                factors.append(
                    RiskFactor(
                        factor_id=f"DQ_{dq.rule_id}",
                        name=f"Data Quality: {dq.rule_name}",
                        description=f"Data quality finding: {dq.message}",
                        contribution=float(dq_w),
                        category="DATA_QUALITY",
                        severity=dq.severity,
                        rule_id=dq.rule_id,
                    )
                )
                contributing_findings.append(dq.rule_id)

        # 6. Raw Score Calculation & Bounds [0, 100]
        raw_score = sum(f.contribution for f in factors)
        score = min(100.0, max(0.0, raw_score))

        # 7. Critical Findings Overrides
        has_critical = any(r.severity == "CRITICAL" for r in failed_statutory) or compliance_decision.hard_override
        if self.config.policy.critical_override.enabled and has_critical:
            floor = self.config.policy.critical_override.min_score_floor
            if score < floor:
                diff = floor - score
                factors.append(
                    RiskFactor(
                        factor_id="CRITICAL_OVERRIDE",
                        name="Critical Finding Policy Floor",
                        description="Policy floor adjustment triggered by CRITICAL statutory failure or hard filing override.",
                        contribution=float(diff),
                        category="POLICY",
                    )
                )
                score = floor

        risk_level = self.level_for_score(score)
        if has_critical and self.config.policy.critical_override.enabled:
            risk_level = self.config.policy.critical_override.min_risk_level

        priority = self.priority_for_level(risk_level, has_critical=has_critical)

        # 8. Category Risk Scores
        category_scores: Dict[str, float] = {}
        for cat, findings in category_findings.items():
            sev_sum = sum(
                getattr(self.config.weights.severity, f.severity or "MEDIUM", 15.0)
                for f in findings
            )
            base_cat_w = getattr(self.config.weights.category, cat, 5.0)
            category_scores[cat] = min(100.0, float(sev_sum + base_cat_w))

        # 9. Confidence Calculation
        confidence_score = 1.0
        confidence_reasons: List[str] = []

        hsn_missing = any(r.rule_id == "HSN_001" and "not found" in r.message.lower() for r in statutory_results)
        if hsn_missing:
            confidence_score -= self.config.policy.confidence.penalties.missing_hsn_master
            confidence_reasons.append("HSN code not found in master catalog")

        if invoice.direction == "AP":
            gstr2b_unmatched = any(r.rule_id == "ITC_001" and "not reflected" in r.message.lower() for r in statutory_results)
            if gstr2b_unmatched:
                confidence_score -= self.config.policy.confidence.penalties.unmatched_gstr2b
                confidence_reasons.append("Invoice not reflected in GSTR-2B")

        if failed_dq:
            confidence_score -= self.config.policy.confidence.penalties.data_quality_failure
            confidence_reasons.append(f"{len(failed_dq)} data quality check(s) flagged")

        confidence_score = max(0.1, min(1.0, round(confidence_score, 2)))
        if confidence_score >= self.config.policy.confidence.high_threshold:
            confidence = ConfidenceLevel.HIGH.value
        elif confidence_score >= self.config.policy.confidence.medium_threshold:
            confidence = ConfidenceLevel.MEDIUM.value
        else:
            confidence = ConfidenceLevel.LOW.value

        # 10. Machine-Readable Explanation (Deterministic, No LLM)
        top_driver_names = [f.name for f in sorted(factors, key=lambda x: x.contribution, reverse=True)[:3]]
        drivers_str = ", ".join(top_driver_names) if top_driver_names else "compliance findings"
        explanation = (
            f"{risk_level.capitalize()} risk (Score: {score:.1f}, Priority: {priority}, Confidence: {confidence}). "
            f"Primary factors: {drivers_str}. "
            f"Compliance verdict: {compliance_decision.status}."
        )

        assessment = RiskAssessment(
            invoice_id=invoice.invoice_number,
            risk_score=round(score, 1),
            risk_level=risk_level,
            priority=priority,
            confidence=confidence,
            confidence_score=confidence_score,
            explanation=explanation,
            risk_factors=factors,
            contributing_findings=contributing_findings,
            category_scores=category_scores,
            severity_contribution=round(severity_contribution, 1),
            data_quality_impact=round(dq_penalty, 1),
            risk_model_version=self.config.policy.model_version,
        )

        # Attach to ComplianceDecision for downstream consumers
        compliance_decision.risk_score = assessment.risk_score
        compliance_decision.risk_level = assessment.risk_level
        compliance_decision.priority = assessment.priority
        compliance_decision.risk_assessment = assessment

        return assessment

    def assess_batch(
        self,
        invoices: List[Invoice],
        validation_reports: List[ValidationReport],
        compliance_decisions: List[ComplianceDecision],
        context: Optional[Any] = None,
    ) -> BatchRiskReport:
        """
        Assess an entire batch of invoices and produce aggregated distribution and top risky lists.
        """
        assessments: List[RiskAssessment] = []
        by_level: Dict[str, int] = {lvl.value: 0 for lvl in RiskLevel}
        by_priority: Dict[str, int] = {p.value: 0 for p in RiskPriority}
        by_category: Dict[str, int] = {}
        total_score = 0.0

        for inv, report, decision in zip(invoices, validation_reports, compliance_decisions):
            assessment = self.assess(inv, report, decision, context=context)
            assessments.append(assessment)

            by_level[assessment.risk_level] = by_level.get(assessment.risk_level, 0) + 1
            by_priority[assessment.priority] = by_priority.get(assessment.priority, 0) + 1
            total_score += assessment.risk_score

            for f in assessment.risk_factors:
                if f.category:
                    by_category[f.category] = by_category.get(f.category, 0) + 1

        total_count = len(assessments)
        avg_score = round(total_score / total_count, 1) if total_count > 0 else 0.0

        # Deterministic top risky sorting: risk_score DESC, then invoice_id ASC
        top_risky = sorted(
            assessments,
            key=lambda a: (-a.risk_score, a.invoice_id)
        )[:10]

        distribution = RiskDistribution(
            total_invoices=total_count,
            by_level=by_level,
            by_priority=by_priority,
            by_category=by_category,
            average_risk_score=avg_score,
        )

        return BatchRiskReport(
            distribution=distribution,
            top_risky_invoices=top_risky,
            assessments=assessments,
            risk_model_version=self.config.policy.model_version,
        )
