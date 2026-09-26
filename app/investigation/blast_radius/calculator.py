"""
app.investigation.blast_radius.calculator
=========================================
Deterministic calculation of financial exposure, risk distributions,
temporal trends, and systemic classifications for Blast Radius Intelligence (Sprint 9).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Set, Tuple

from app.investigation.config.investigation_config import (
    BlastRadiusPolicyConfig,
    InvestigationConfig,
    default_investigation_config,
)
from app.investigation.enums import SystemicClassification, TrendClassification
from app.investigation.evidence.models import EvidenceContext


def calculate_financial_blast_radius(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[Decimal, Decimal, Decimal, Dict[str, Decimal]]:
    """
    Reconcile financial impact across the affected cohort strictly using S6 authoritative data.
    Ensures zero double-counting.
    Returns (total_exposure, average_exposure, max_exposure, exposure_by_type).
    """
    total = Decimal("0.00")
    max_exp = Decimal("0.00")
    by_type: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    count_with_exposure = 0

    for inv_id in target_invoice_ids:
        fi = ctx.financial_impacts_map.get(inv_id)
        if fi and fi.potential_exposure and fi.potential_exposure > Decimal("0.00"):
            exp = fi.potential_exposure
            total += exp
            if exp > max_exp:
                max_exp = exp
            count_with_exposure += 1
            t_name = fi.impact_type.value if hasattr(fi.impact_type, "value") else str(fi.impact_type)
            by_type[t_name] += exp

    divisor = count_with_exposure if count_with_exposure > 0 else 1
    avg_exp = (total / Decimal(divisor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    max_exp = max_exp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return total, avg_exp, max_exp, dict(by_type)


def calculate_risk_blast_radius(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Extract severity and priority distributions across the cohort directly from S3 risk truth.
    Returns (severity_distribution, priority_distribution).
    """
    sev_counts: Counter[str] = Counter({"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0})
    pri_counts: Counter[str] = Counter({"P1": 0, "P2": 0, "P3": 0, "P4": 0})

    for inv_id in target_invoice_ids:
        d = ctx.decision_map.get(inv_id)
        if d:
            lvl = getattr(d, "risk_level", None) or "LOW"
            pri = getattr(d, "priority", None) or "P4"
            sev_counts[lvl] += 1
            pri_counts[pri] += 1

    return dict(sev_counts), dict(pri_counts)


def classify_temporal_trend(
    period_distribution: Dict[str, int],
    policy: Optional[BlastRadiusPolicyConfig] = None,
) -> TrendClassification:
    """
    Classify temporal growth deterministically based on sequential monthly activity.
    """
    p_config = (policy or default_investigation_config.blast_radius).trend_analysis
    sorted_periods = sorted([p for p in period_distribution.keys() if p != "UNKNOWN_PERIOD"])

    if len(sorted_periods) < p_config.min_periods_required:
        return TrendClassification.INSUFFICIENT_DATA

    counts = [period_distribution[p] for p in sorted_periods]
    total = sum(counts)

    # 1. Sudden Onset Check (Recent sharp spike from baseline zero/low)
    latest = counts[-1]
    if total > 0 and (latest / total) >= p_config.sudden_onset_ratio and len(counts) >= 2:
        if sum(counts[:-1]) <= latest * 0.5:
            return TrendClassification.SUDDEN_ONSET

    # 2. Recovering Check (Prior activity dropping sharply to zero/low)
    if len(counts) >= 2 and counts[-2] > 0 and latest < counts[-2] * 0.2:
        return TrendClassification.RECOVERING

    # 3. Expansion / Contraction Check
    first_val = counts[0]
    last_val = counts[-1]
    if first_val > 0:
        pct_change = ((last_val - first_val) / first_val) * 100.0
    else:
        pct_change = 100.0 if last_val > 0 else 0.0

    # Monotonic checks
    is_strictly_increasing = all(counts[i] <= counts[i + 1] for i in range(len(counts) - 1)) and last_val > first_val
    is_strictly_decreasing = all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)) and last_val < first_val

    if is_strictly_increasing or pct_change >= p_config.expansion_threshold_pct:
        return TrendClassification.EXPANDING
    elif is_strictly_decreasing or pct_change <= p_config.contraction_threshold_pct:
        return TrendClassification.CONTRACTING
    else:
        return TrendClassification.STABLE


def classify_systemic_scope(
    affected_count: int,
    total_portfolio_count: int,
    counterparty_count: int,
    period_count: int,
    rule_count: int,
    top_counterparty_share: float,
    top_rule_share: float,
    trend: TrendClassification,
    policy: Optional[BlastRadiusPolicyConfig] = None,
) -> SystemicClassification:
    """
    Deterministically classify whether the observed issue is ISOLATED, CONCENTRATED,
    SYSTEMIC, or EMERGING_SYSTEMIC according to policy rules.
    """
    p_config = (policy or default_investigation_config.blast_radius).classification

    if affected_count <= 0:
        return SystemicClassification.INSUFFICIENT_DATA

    total = max(total_portfolio_count, 1)
    affected_ratio = affected_count / total

    # 1. Isolated Check
    if (
        affected_count <= p_config.isolated_max_invoices
        and counterparty_count <= p_config.isolated_max_counterparties
        and affected_ratio <= p_config.isolated_max_ratio
    ):
        return SystemicClassification.ISOLATED

    # 2. Emerging Systemic Check (Expanding across multiple periods or counterparties)
    if trend == TrendClassification.EXPANDING and (counterparty_count >= 2 or period_count >= 2):
        return SystemicClassification.EMERGING_SYSTEMIC

    # 3. Systemic Check (Broad organizational/supplier/period footprint)
    if (
        counterparty_count >= p_config.systemic_min_counterparties
        and period_count >= p_config.systemic_min_periods
    ) or (affected_ratio >= p_config.systemic_min_ratio and counterparty_count >= 2):
        return SystemicClassification.SYSTEMIC

    # 4. Concentrated Check (Dominant single counterparty or single rule)
    if (
        top_counterparty_share >= p_config.concentrated_share_threshold
        or top_rule_share >= p_config.concentrated_share_threshold
    ):
        return SystemicClassification.CONCENTRATED

    # Fallback to systemic if moderate count across vendors
    if affected_count >= p_config.min_population_for_systemic and counterparty_count >= 2:
        return SystemicClassification.SYSTEMIC

    return SystemicClassification.CONCENTRATED
