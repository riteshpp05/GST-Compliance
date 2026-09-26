"""
app.investigation.root_cause.patterns
=====================================
Deterministic pattern detection algorithms across compliance rules, counterparties,
temporal sequences, commodity codes (HSN), geographic jurisdictions, duplicates, and anomalies.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from app.investigation.evidence.models import EvidenceContext


def analyze_rule_patterns(ctx: EvidenceContext) -> Dict[str, Dict[str, Any]]:
    """
    Analyze rule failure patterns across all failed invoices.
    Returns mapping: rule_id -> {affected_invoice_ids, count, gate_no, sample_messages}
    """
    patterns: Dict[str, Dict[str, Any]] = {}
    for rule_id, inv_set in ctx.failed_invoices_by_rule.items():
        if not inv_set:
            continue
        details = ctx.rule_failure_details.get(rule_id, [])
        gate_nos = {g.gate_no for g in details if g.gate_no is not None}
        gate_no = next(iter(gate_nos)) if gate_nos else None
        sample_msgs = [g.message for g in details if g.message][:3]

        patterns[rule_id] = {
            "rule_id": rule_id,
            "affected_invoice_ids": sorted(inv_set),
            "count": len(inv_set),
            "gate_no": gate_no,
            "sample_messages": sample_msgs,
        }
    return patterns


def analyze_counterparty_patterns(
    ctx: EvidenceContext,
    target_invoice_ids: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Analyze counterparty concentration within target invoices (or all failed invoices).
    Returns mapping: cp_id -> {affected_count, total_count, share, name, invoice_ids}
    """
    scope_invoices = target_invoice_ids if target_invoice_ids is not None else ctx.failed_invoices
    if not scope_invoices:
        return {}

    total_in_scope = len(scope_invoices)
    cp_counts: Counter[str] = Counter()
    cp_invoices: Dict[str, List[str]] = defaultdict(list)

    for inv_id in scope_invoices:
        inv = ctx.invoice_map.get(inv_id)
        if inv:
            cp_id = inv.counterparty_gstin or inv.gstin or inv.counterparty_name
            cp_counts[cp_id] += 1
            cp_invoices[cp_id].append(inv_id)

    patterns: Dict[str, Dict[str, Any]] = {}
    for cp_id, aff_count in cp_counts.items():
        total_for_cp = len(ctx.invoices_by_counterparty.get(cp_id, set()))
        share = aff_count / total_in_scope if total_in_scope > 0 else 0.0
        patterns[cp_id] = {
            "counterparty_id": cp_id,
            "counterparty_name": ctx.counterparty_names.get(cp_id, cp_id),
            "affected_count": aff_count,
            "total_count": total_for_cp,
            "share_of_affected": share,
            "invoice_ids": sorted(cp_invoices[cp_id]),
        }
    return patterns


def analyze_temporal_patterns(
    ctx: EvidenceContext,
    target_invoice_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Analyze temporal recurrence and persistence of issues across tax periods.
    """
    scope_invoices = target_invoice_ids if target_invoice_ids is not None else ctx.failed_invoices
    if not scope_invoices:
        return {
            "periods": [],
            "period_counts": {},
            "first_period": None,
            "last_period": None,
            "duration_months": 0,
        }

    period_counts: Counter[str] = Counter()
    for inv_id in scope_invoices:
        for period, period_invs in ctx.invoices_by_period.items():
            if inv_id in period_invs:
                period_counts[period] += 1
                break

    sorted_periods = sorted([p for p in period_counts.keys() if p != "UNKNOWN_PERIOD"])
    return {
        "periods": sorted_periods,
        "period_counts": dict(period_counts),
        "first_period": sorted_periods[0] if sorted_periods else None,
        "last_period": sorted_periods[-1] if sorted_periods else None,
        "duration_months": len(sorted_periods),
    }


def analyze_hsn_patterns(
    ctx: EvidenceContext,
    target_invoice_ids: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Analyze commodity HSN code concentration within target population."""
    scope_invoices = target_invoice_ids if target_invoice_ids is not None else ctx.failed_invoices
    if not scope_invoices:
        return {}

    total_in_scope = len(scope_invoices)
    hsn_counts: Counter[str] = Counter()
    hsn_invoices: Dict[str, List[str]] = defaultdict(list)

    for inv_id in scope_invoices:
        inv = ctx.invoice_map.get(inv_id)
        if inv:
            hsn = inv.hsn_sac or getattr(inv, "hsn_code", "")
            if hsn:
                hsn_counts[hsn] += 1
                hsn_invoices[hsn].append(inv_id)

    patterns: Dict[str, Dict[str, Any]] = {}
    for hsn, count in hsn_counts.items():
        share = count / total_in_scope if total_in_scope > 0 else 0.0
        patterns[hsn] = {
            "hsn_code": hsn,
            "affected_count": count,
            "share_of_affected": share,
            "invoice_ids": sorted(hsn_invoices[hsn]),
        }
    return patterns


def analyze_state_patterns(
    ctx: EvidenceContext,
    target_invoice_ids: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Analyze place-of-supply / geographic state concentration."""
    scope_invoices = target_invoice_ids if target_invoice_ids is not None else ctx.failed_invoices
    if not scope_invoices:
        return {}

    total_in_scope = len(scope_invoices)
    state_counts: Counter[str] = Counter()
    state_invoices: Dict[str, List[str]] = defaultdict(list)

    for inv_id in scope_invoices:
        inv = ctx.invoice_map.get(inv_id)
        if inv:
            state = inv.place_of_supply or getattr(inv, "buyer_state", "") or ""
            if state:
                state_counts[state] += 1
                state_invoices[state].append(inv_id)

    patterns: Dict[str, Dict[str, Any]] = {}
    for state, count in state_counts.items():
        share = count / total_in_scope if total_in_scope > 0 else 0.0
        patterns[state] = {
            "state": state,
            "affected_count": count,
            "share_of_affected": share,
            "invoice_ids": sorted(state_invoices[state]),
        }
    return patterns


def get_financial_exposure_for_population(
    ctx: EvidenceContext,
    target_invoice_ids: Set[str],
) -> Tuple[Decimal, Dict[str, Decimal]]:
    """
    Sum potential exposure for a population strictly from S6 financial impacts.
    Reconciles directly with S6 truth without double counting.
    """
    total = Decimal("0.00")
    by_type: Dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for inv_id in target_invoice_ids:
        fi = ctx.financial_impacts_map.get(inv_id)
        if fi and fi.potential_exposure:
            exp = fi.potential_exposure
            total += exp
            type_key = fi.impact_type.value if hasattr(fi.impact_type, "value") else str(fi.impact_type)
            by_type[type_key] += exp

    return total, dict(by_type)
