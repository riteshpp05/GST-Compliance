"""
app.investigation.blast_radius.dimensions
=========================================
Multi-dimensional analysis tools for Blast Radius Intelligence (Sprint 9).
Slices affected invoice cohorts across transactions, counterparties, rules,
tax periods, HSN commodities, and geographic states.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from app.investigation.evidence.collector import extract_period
from app.investigation.evidence.models import EvidenceContext


def summarize_invoices(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[int, float, List[str]]:
    """Return count, ratio of total portfolio, and sorted list of invoice IDs."""
    count = len(target_invoice_ids)
    total = max(ctx.total_invoices, 1)
    ratio = count / total
    return count, ratio, sorted(target_invoice_ids)


def summarize_counterparties(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[int, List[str], Optional[str], float]:
    """
    Summarize counterparties in target population.
    Returns (unique_count, sorted_list, top_counterparty_id, top_share).
    """
    cp_counts: Counter[str] = Counter()
    for inv_id in target_invoice_ids:
        inv = ctx.invoice_map.get(inv_id)
        if inv:
            cp_id = inv.counterparty_gstin or inv.gstin or inv.counterparty_name
            cp_counts[cp_id] += 1

    total_in_scope = len(target_invoice_ids)
    unique_count = len(cp_counts)
    sorted_cps = sorted(cp_counts.keys())

    top_cp_id = None
    top_share = 0.0
    if cp_counts:
        top_cp_id, top_count = cp_counts.most_common(1)[0]
        top_share = top_count / total_in_scope if total_in_scope > 0 else 0.0

    return unique_count, sorted_cps, top_cp_id, top_share


def summarize_rules(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[int, List[str], Optional[str], float]:
    """
    Summarize failed rules in target population.
    Returns (unique_rule_count, sorted_rules, top_rule_id, top_rule_share).
    """
    rule_counts: Counter[str] = Counter()
    for inv_id in target_invoice_ids:
        d = ctx.decision_map.get(inv_id)
        if d:
            for g in getattr(d, "gates", []):
                if g.status in ("FAIL", "FAILED", "NON_COMPLIANT"):
                    r_id = g.rule_id or g.name
                    rule_counts[r_id] += 1

    total_in_scope = len(target_invoice_ids)
    unique_count = len(rule_counts)
    sorted_rules = sorted(rule_counts.keys())

    top_rule_id = None
    top_share = 0.0
    if rule_counts:
        top_rule_id, top_count = rule_counts.most_common(1)[0]
        top_share = top_count / total_in_scope if total_in_scope > 0 else 0.0

    return unique_count, sorted_rules, top_rule_id, top_share


def summarize_periods(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[int, List[str], Dict[str, int], Optional[str], Optional[str], Optional[str], float]:
    """
    Summarize tax periods in target population.
    Returns (unique_count, sorted_periods, distribution, first_period, last_period, top_period, top_share).
    """
    period_counts: Counter[str] = Counter()
    for inv_id in target_invoice_ids:
        inv = ctx.invoice_map.get(inv_id)
        if inv:
            p = extract_period(inv.invoice_date)
            if p != "UNKNOWN_PERIOD":
                period_counts[p] += 1

    total_in_scope = len(target_invoice_ids)
    sorted_periods = sorted(period_counts.keys())
    unique_count = len(sorted_periods)

    first_p = sorted_periods[0] if sorted_periods else None
    last_p = sorted_periods[-1] if sorted_periods else None

    top_p = None
    top_share = 0.0
    if period_counts:
        top_p, top_cnt = period_counts.most_common(1)[0]
        top_share = top_cnt / total_in_scope if total_in_scope > 0 else 0.0

    return unique_count, sorted_periods, dict(period_counts), first_p, last_p, top_p, top_share


def summarize_hsns(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[int, List[str], Optional[str], float]:
    """Summarize HSN commodity codes. Returns (count, list, top_hsn, top_share)."""
    hsn_counts: Counter[str] = Counter()
    for inv_id in target_invoice_ids:
        inv = ctx.invoice_map.get(inv_id)
        if inv:
            hsn = inv.hsn_sac or getattr(inv, "hsn_code", "")
            if hsn:
                hsn_counts[hsn] += 1

    total_in_scope = len(target_invoice_ids)
    unique_count = len(hsn_counts)
    sorted_hsns = sorted(hsn_counts.keys())

    top_hsn = None
    top_share = 0.0
    if hsn_counts:
        top_hsn, top_cnt = hsn_counts.most_common(1)[0]
        top_share = top_cnt / total_in_scope if total_in_scope > 0 else 0.0

    return unique_count, sorted_hsns, top_hsn, top_share


def summarize_states(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[int, List[str], Optional[str], float]:
    """Summarize Place of Supply / States. Returns (count, list, top_state, top_share)."""
    state_counts: Counter[str] = Counter()
    for inv_id in target_invoice_ids:
        inv = ctx.invoice_map.get(inv_id)
        if inv:
            st = inv.place_of_supply or getattr(inv, "buyer_state", "") or ""
            if st:
                state_counts[st] += 1

    total_in_scope = len(target_invoice_ids)
    unique_count = len(state_counts)
    sorted_states = sorted(state_counts.keys())

    top_state = None
    top_share = 0.0
    if state_counts:
        top_state, top_cnt = state_counts.most_common(1)[0]
        top_share = top_cnt / total_in_scope if total_in_scope > 0 else 0.0

    return unique_count, sorted_states, top_state, top_share


def summarize_intelligence_overlap(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[int, int, int, List[str], List[str]]:
    """
    Summarize S7 Duplicate & Anomaly presence and exact overlap within target population.
    Returns (duplicate_count, anomaly_count, overlap_count, duplicate_candidate_ids, anomaly_finding_ids).
    """
    dup_invs = {inv_id for inv_id in target_invoice_ids if inv_id in ctx.duplicates_map}
    anom_invs = {inv_id for inv_id in target_invoice_ids if inv_id in ctx.anomalies_map}
    overlap = dup_invs.intersection(anom_invs)

    dup_cand_ids: Set[str] = set()
    for inv_id in dup_invs:
        for c in ctx.duplicates_map.get(inv_id, []):
            dup_cand_ids.add(c.candidate_id)

    anom_ids: Set[str] = set()
    for inv_id in anom_invs:
        for a in ctx.anomalies_map.get(inv_id, []):
            anom_ids.add(a.finding_id)

    return len(dup_invs), len(anom_invs), len(overlap), sorted(dup_cand_ids), sorted(anom_ids)
