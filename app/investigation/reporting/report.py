"""
app.investigation.reporting.report
==================================
Reporting module for Root Cause & Blast Radius Intelligence.
Provides human-readable CLI formatting, strict separation of observed facts vs. inferences,
and structured text summaries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.investigation.models import InvestigationProfile, RootCauseFinding, BlastRadiusProfile


class InvestigationReportFormatter:
    """
    Renders structured, audit-compliant text reports from an InvestigationProfile.
    Enforces clear separation:
      1. Observed Facts
      2. Inferred Patterns
      3. Root Cause Candidates (with Causality-Safe Statements)
      4. Multidimensional Blast Radius
      5. Financial Impact & Risk Profile
      6. Recommended Next Actions for AI Agent
    """

    @staticmethod
    def format_cli_summary(profile: InvestigationProfile) -> str:
        """Render high-level CLI summary matching project specification."""
        lines: List[str] = []
        sep = "=" * 65

        lines.append("\n" + sep)
        lines.append("UC15 ROOT CAUSE & IMPACT INTELLIGENCE")
        lines.append(sep)
        lines.append(f"\nInvestigation: {profile.investigation_id}")

        rc = profile.primary_root_cause
        if rc:
            lines.append(f"\nPrimary Root Cause:")
            lines.append(f"{rc.root_cause_type.value}")
            lines.append(f"\nConfidence:")
            lines.append(f"{rc.confidence.value} (Likelihood: {rc.likelihood.value}, Score: {rc.score.total_score:.1f}/100)")
            lines.append(f"\nEvidence:")
            lines.append(f"- {len(rc.affected_invoice_ids)} affected invoice(s)")
            for e in rc.evidence[:5]:
                lines.append(f"- {e.title}")
            lines.append(f"\nCausality Statement:")
            lines.append(f"\"{rc.causality_statement}\"")
        else:
            lines.append("\nPrimary Root Cause: None (No compliance failures detected)")

        br = profile.blast_radius
        if br and br.affected_invoice_count > 0:
            lines.append(f"\nBlast Radius:")
            lines.append(f"Invoices:          {br.affected_invoice_count:<6} ({br.affected_ratio * 100:.1f}% of portfolio)")
            lines.append(f"Counterparties:    {br.affected_counterparty_count}")
            lines.append(f"Rules:             {br.affected_rule_count}")
            lines.append(f"Periods:           {br.affected_period_count}")
            lines.append(f"HSN Categories:    {br.affected_hsn_count}")
            lines.append(f"States:            {br.affected_state_count}")

            lines.append(f"\nPotential Exposure:")
            lines.append(f"INR {br.total_potential_exposure:,.2f} (Avg: INR {br.average_exposure:,.2f})")

            lines.append(f"\nTrend:")
            lines.append(f"{br.trend.value}")

            lines.append(f"\nClassification:")
            lines.append(f"{br.systemic_classification.value}")

            if br.top_counterparty_id:
                lines.append(f"\nConcentration:")
                lines.append(f"Top Counterparty:  {br.top_counterparty_id} ({br.top_counterparty_share * 100:.1f}%)")
                if br.top_rule_id:
                    lines.append(f"Top Rule:          {br.top_rule_id} ({br.top_rule_share * 100:.1f}%)")

            if br.duplicate_affected_count > 0 or br.anomaly_affected_count > 0:
                lines.append(f"\nIntelligence Overlap:")
                lines.append(f"Duplicates:        {br.duplicate_affected_count} invoices")
                lines.append(f"Anomalies:         {br.anomaly_affected_count} invoices")
                lines.append(f"Compound Overlap:  {br.duplicate_and_anomaly_overlap_count} invoices")
        else:
            lines.append("\nBlast Radius: Clean portfolio (0 affected transactions)")

        if profile.recommended_investigation_areas:
            lines.append(f"\nRecommended Next Areas for Investigation:")
            for idx, rec in enumerate(profile.recommended_investigation_areas[:3], 1):
                lines.append(f"{idx}. {rec}")

        lines.append(sep + "\n")
        return "\n".join(lines)

    @staticmethod
    def format_root_causes_detail(profile: InvestigationProfile) -> str:
        """Render detailed breakdown of all ranked candidate root causes."""
        lines: List[str] = []
        sep = "-" * 75
        lines.append("\n" + "=" * 75)
        lines.append(f"  ROOT CAUSE CANDIDATE ANALYSIS ({len(profile.root_cause_candidates)} Candidates)")
        lines.append("=" * 75)

        if not profile.root_cause_candidates:
            lines.append("  No root-cause candidates identified. Portfolio is compliant.")
            lines.append("=" * 75 + "\n")
            return "\n".join(lines)

        for idx, rc in enumerate(profile.root_cause_candidates, 1):
            is_prim = " [PRIMARY]" if rc == profile.primary_root_cause else " [CONTRIBUTING]"
            lines.append(f"\n#{idx} {rc.title}{is_prim}")
            lines.append(sep)
            lines.append(f"  Type:        {rc.root_cause_type.value}")
            lines.append(f"  Confidence:  {rc.confidence.value}  |  Likelihood: {rc.likelihood.value}  |  Severity: {rc.severity}")
            sc = rc.score
            lines.append(
                f"  Score:       {sc.total_score:.1f}/100  (Evid: {sc.evidence_strength:.1f}, "
                f"Recurr: {sc.pattern_recurrence:.1f}, Cov: {sc.population_coverage:.1f}, "
                f"Temp: {sc.temporal_consistency:.1f}, CP: {sc.counterparty_concentration:.1f}, Rule: {sc.rule_concentration:.1f})"
            )
            lines.append(f"  Invoices:    {len(rc.affected_invoice_ids)} affected: {', '.join(rc.affected_invoice_ids[:6])}")
            lines.append(f"  Exposure:    INR {rc.financial_exposure:,.2f}")
            lines.append(f"  Causality:   \"{rc.causality_statement}\"")
            lines.append("  Evidence Items:")
            for e in rc.evidence:
                lines.append(f"    - [{e.evidence_type.value}] {e.title}")

        lines.append("\n" + "=" * 75 + "\n")
        return "\n".join(lines)

    @staticmethod
    def format_blast_radius_detail(profile: InvestigationProfile) -> str:
        """Render multi-dimensional blast radius analysis report."""
        lines: List[str] = []
        sep = "-" * 75
        lines.append("\n" + "=" * 75)
        lines.append("  MULTIDIMENSIONAL BLAST RADIUS INTELLIGENCE REPORT")
        lines.append("=" * 75)

        br = profile.blast_radius
        if not br:
            lines.append("  No blast radius calculated.")
            lines.append("=" * 75 + "\n")
            return "\n".join(lines)

        lines.append(f"  Blast Radius ID:    {br.blast_radius_id}")
        lines.append(f"  Root Cause Scope:   {br.root_cause_id}")
        lines.append(f"  Classification:     {br.systemic_classification.value}")
        lines.append(f"  Temporal Trend:     {br.trend.value}")
        lines.append(sep)
        lines.append("  DIMENSIONAL SPREAD:")
        lines.append(f"    Invoices:         {br.affected_invoice_count} / {br.total_population_count} ({br.affected_ratio * 100:.1f}%)")
        lines.append(f"    Counterparties:   {br.affected_counterparty_count} (Top: {br.top_counterparty_id or 'N/A'}, {br.top_counterparty_share * 100:.1f}%)")
        lines.append(f"    Rules Failed:     {br.affected_rule_count} (Top: {br.top_rule_id or 'N/A'}, {br.top_rule_share * 100:.1f}%)")
        lines.append(f"    Periods Active:   {br.affected_period_count} ({br.first_detected_period or 'N/A'} to {br.last_detected_period or 'N/A'})")
        lines.append(f"    HSN Codes:        {br.affected_hsn_count} (Top: {br.top_hsn or 'N/A'}, {br.top_hsn_share * 100:.1f}%)")
        lines.append(f"    States (POS):     {br.affected_state_count} (Top: {br.top_state or 'N/A'}, {br.top_state_share * 100:.1f}%)")
        lines.append(sep)
        lines.append("  FINANCIAL IMPACT (Reconciled from S6 Truth):")
        lines.append(f"    Total Exposure:   INR {br.total_potential_exposure:,.2f}")
        lines.append(f"    Average Exposure: INR {br.average_exposure:,.2f}")
        lines.append(f"    Maximum Exposure: INR {br.maximum_exposure:,.2f}")
        for t_name, val in br.exposure_by_type.items():
            lines.append(f"      * {t_name}: INR {val:,.2f}")
        lines.append(sep)
        lines.append("  RISK SEVERITY (Reconciled from S3 Risk Truth):")
        lines.append(f"    Severities:       {br.severity_distribution}")
        lines.append(f"    Priorities:       {br.priority_distribution}")
        lines.append(sep)
        lines.append("  INTELLIGENCE OVERLAP (Reconciled from S7 Truth):")
        lines.append(f"    Duplicate Invoices: {br.duplicate_affected_count}")
        lines.append(f"    Anomaly Invoices:   {br.anomaly_affected_count}")
        lines.append(f"    Compound Overlap:   {br.duplicate_and_anomaly_overlap_count}")
        lines.append("=" * 75 + "\n")
        return "\n".join(lines)
