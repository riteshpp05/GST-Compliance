"""
app.investigation.blast_radius.engine
=====================================
Blast Radius Intelligence Engine (Sprint 9).
Quantifies the affected population, exposure, trend dynamics,
counterparty concentration, and organizational systemic boundaries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.investigation.blast_radius.calculator import (
    calculate_financial_blast_radius,
    calculate_risk_blast_radius,
    classify_systemic_scope,
    classify_temporal_trend,
)
from app.investigation.blast_radius.dimensions import (
    summarize_counterparties,
    summarize_hsns,
    summarize_intelligence_overlap,
    summarize_invoices,
    summarize_periods,
    summarize_rules,
    summarize_states,
)
from app.investigation.config.investigation_config import (
    InvestigationConfig,
    default_investigation_config,
)
from app.investigation.evidence.models import EvidenceContext
from app.investigation.models import BlastRadiusProfile


class BlastRadiusEngine:
    """
    Computes comprehensive BlastRadiusProfile for a given root-cause cohort or overall discrepancy cohort.
    """

    def __init__(self, config: Optional[InvestigationConfig] = None) -> None:
        self.config = config or default_investigation_config
        self.policy = self.config.blast_radius

    def calculate_profile(
        self,
        ctx: EvidenceContext,
        target_invoice_ids: Set[str],
        root_cause_id: str = "GENERIC_INVESTIGATION",
    ) -> BlastRadiusProfile:
        """
        Calculate full BlastRadiusProfile across all statutory and operational dimensions.
        """
        if not target_invoice_ids:
            return BlastRadiusProfile(
                blast_radius_id=f"BR-{root_cause_id}",
                root_cause_id=root_cause_id,
                total_population_count=ctx.total_invoices,
            )

        # 1. Invoice Summary
        inv_count, aff_ratio, inv_list = summarize_invoices(ctx, target_invoice_ids)

        # 2. Counterparty Summary
        cp_count, cp_list, top_cp_id, top_cp_share = summarize_counterparties(ctx, target_invoice_ids)

        # 3. Rule Summary
        rule_count, rule_list, top_rule_id, top_rule_share = summarize_rules(ctx, target_invoice_ids)

        # 4. Period Summary
        p_count, p_list, p_dist, first_p, last_p, top_p, top_p_share = summarize_periods(ctx, target_invoice_ids)

        # 5. HSN Summary
        hsn_count, hsn_list, top_hsn, top_hsn_share = summarize_hsns(ctx, target_invoice_ids)

        # 6. State Summary
        st_count, st_list, top_st, top_st_share = summarize_states(ctx, target_invoice_ids)

        # 7. S7 Duplicate & Anomaly Overlap
        dup_cnt, anom_cnt, overlap_cnt, dup_ids, anom_ids = summarize_intelligence_overlap(ctx, target_invoice_ids)

        # 8. Financial Exposure (S6 Truth)
        tot_exp, avg_exp, max_exp, exp_by_type = calculate_financial_blast_radius(ctx, target_invoice_ids)

        # 9. Risk Distribution (S3 Truth)
        sev_dist, pri_dist = calculate_risk_blast_radius(ctx, target_invoice_ids)

        # 10. Temporal Trend
        trend = classify_temporal_trend(p_dist, policy=self.policy)

        # 11. Systemic Scope Classification
        systemic_cls = classify_systemic_scope(
            affected_count=inv_count,
            total_portfolio_count=ctx.total_invoices,
            counterparty_count=cp_count,
            period_count=p_count,
            rule_count=rule_count,
            top_counterparty_share=top_cp_share,
            top_rule_share=top_rule_share,
            trend=trend,
            policy=self.policy,
        )

        return BlastRadiusProfile(
            blast_radius_id=f"BR-{root_cause_id}",
            root_cause_id=root_cause_id,
            total_population_count=ctx.total_invoices,
            affected_invoice_count=inv_count,
            affected_ratio=aff_ratio,
            affected_counterparty_count=cp_count,
            affected_rule_count=rule_count,
            affected_period_count=p_count,
            affected_hsn_count=hsn_count,
            affected_state_count=st_count,
            affected_invoice_ids=inv_list,
            affected_counterparties=cp_list,
            affected_rules=rule_list,
            affected_periods=p_list,
            affected_hsns=hsn_list,
            affected_states=st_list,
            total_potential_exposure=tot_exp,
            average_exposure=avg_exp,
            maximum_exposure=max_exp,
            exposure_by_type=exp_by_type,
            first_detected_period=first_p,
            last_detected_period=last_p,
            duration_periods=len(p_list),
            period_distribution=p_dist,
            trend=trend,
            severity_distribution=sev_dist,
            priority_distribution=pri_dist,
            duplicate_affected_count=dup_cnt,
            anomaly_affected_count=anom_cnt,
            duplicate_and_anomaly_overlap_count=overlap_cnt,
            duplicate_candidate_ids=dup_ids,
            anomaly_finding_ids=anom_ids,
            top_counterparty_share=top_cp_share,
            top_counterparty_id=top_cp_id,
            top_rule_share=top_rule_share,
            top_rule_id=top_rule_id,
            top_period_share=top_p_share,
            top_period=top_p,
            top_hsn_share=top_hsn_share,
            top_hsn=top_hsn,
            top_state_share=top_st_share,
            top_state=top_st,
            systemic_classification=systemic_cls,
            detector_version="1.0",
            lineage={
                "target_population_size": len(target_invoice_ids),
                "source": "blast_radius_engine_v1.0",
            },
        )
