"""
app.intelligence.duplicate.near_detector
========================================
Deterministic near-duplicate detector using transparent structured-field scoring.
Includes false-positive protection for recurring transactions and non-matching invoice numbers.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.domain.models.invoice import Invoice
from app.intelligence.common.enums import (
    DuplicateMatchType,
    IntelligenceConfidence,
)
from app.intelligence.config.intelligence_config import (
    DuplicatePolicyConfig,
    default_intelligence_config,
)
from app.intelligence.duplicate.fingerprint import (
    compute_string_similarity,
    extract_parties,
    normalize_date,
    normalize_invoice_number,
    parse_decimal_safe,
)
from app.intelligence.duplicate.models import DuplicateCandidate


class NearDuplicateDetector:
    """
    Evaluates similarity across 6 structured attributes with configurable weights.
    Applies explicit false-positive controls for legitimate recurring transactions.
    """
    DETECTOR_NAME = "NEAR_DUPLICATE_DETECTOR"
    DETECTOR_VERSION = "1.0"

    def __init__(self, config: Optional[DuplicatePolicyConfig] = None) -> None:
        self.config = config or default_intelligence_config.duplicate

    def compare_pair(self, inv1: Invoice, inv2: Invoice) -> DuplicateCandidate:
        """
        Compare two distinct invoices and compute deterministic structured similarity.
        """
        if inv1.invoice_id == inv2.invoice_id:
            return DuplicateCandidate(
                source_invoice_id=inv1.invoice_id,
                matched_invoice_id=inv2.invoice_id,
                match_type=DuplicateMatchType.NO_DUPLICATE,
                similarity_score=0.0,
                confidence=IntelligenceConfidence.LOW,
            )

        # 1. Missing data checks
        raw_inv1 = inv1.invoice_number
        raw_inv2 = inv2.invoice_number
        sup1, buy1 = extract_parties(inv1)
        sup2, buy2 = extract_parties(inv2)

        if not raw_inv1 or not raw_inv2 or not sup1 or not sup2:
            return DuplicateCandidate(
                source_invoice_id=inv1.invoice_id,
                matched_invoice_id=inv2.invoice_id,
                match_type=DuplicateMatchType.NOT_EVALUATED,
                similarity_score=0.0,
                confidence=IntelligenceConfidence.LOW,
                evidence={
                    "status": "NOT_EVALUATED",
                    "reason": "Missing critical fields required for duplicate evaluation.",
                },
            )

        weights = self.config.weights
        thresholds = self.config.thresholds
        field_scores: Dict[str, float] = {}
        field_matches: Dict[str, bool] = {}

        # 2. Supplier GSTIN Match (Weight: 30)
        if sup1 == sup2:
            field_scores["supplier_gstin"] = weights.supplier_gstin_match
            field_matches["supplier_gstin"] = True
        else:
            field_scores["supplier_gstin"] = 0.0
            field_matches["supplier_gstin"] = False

        # 3. Buyer GSTIN Match (Weight: 15)
        if buy1 and buy2 and buy1 == buy2:
            field_scores["buyer_gstin"] = weights.buyer_gstin_match
            field_matches["buyer_gstin"] = True
        elif not buy1 and not buy2 and getattr(inv1, "counterparty_name", "") == getattr(inv2, "counterparty_name", ""):
            field_scores["buyer_gstin"] = weights.buyer_gstin_match * 0.8
            field_matches["buyer_gstin"] = True
        else:
            field_scores["buyer_gstin"] = 0.0
            field_matches["buyer_gstin"] = False

        # 4. Invoice Number Similarity (Weight: 25)
        norm_inv1 = normalize_invoice_number(raw_inv1, self.config.normalization.remove_separators)
        norm_inv2 = normalize_invoice_number(raw_inv2, self.config.normalization.remove_separators)
        num_sim = compute_string_similarity(norm_inv1, norm_inv2)
        field_scores["invoice_number"] = round(num_sim * weights.invoice_number_similarity, 2)
        field_matches["invoice_number"] = num_sim >= 0.85

        # 5. Date Proximity (Weight: 15)
        date_score = 0.0
        date_match = False
        dt1_str = normalize_date(inv1.invoice_date)
        dt2_str = normalize_date(inv2.invoice_date)
        days_diff: Optional[int] = None

        if dt1_str and dt2_str:
            try:
                d1 = datetime.strptime(dt1_str, "%Y-%m-%d").date()
                d2 = datetime.strptime(dt2_str, "%Y-%m-%d").date()
                days_diff = abs((d1 - d2).days)
                if days_diff == 0:
                    date_score = weights.date_proximity
                    date_match = True
                elif days_diff <= self.config.date_proximity_brackets.tight_days:
                    date_score = weights.date_proximity * 0.80
                    date_match = True
                elif days_diff <= self.config.date_proximity_brackets.moderate_days:
                    date_score = weights.date_proximity * 0.50
                    date_match = True
                elif days_diff <= self.config.date_proximity_brackets.loose_days:
                    date_score = weights.date_proximity * 0.25
            except Exception:
                date_score = 0.0

        field_scores["date_proximity"] = round(date_score, 2)
        field_matches["date_proximity"] = date_match

        # 6. Taxable Value Similarity (Weight: 10)
        v1 = parse_decimal_safe(inv1.taxable_value)
        v2 = parse_decimal_safe(inv2.taxable_value)
        val_score = 0.0
        val_match = False
        if v1 > Decimal("0.00") and v2 > Decimal("0.00"):
            max_v = max(v1, v2)
            pct_diff = float((abs(v1 - v2) / max_v) * Decimal("100.00"))
            if pct_diff == 0.0:
                val_score = weights.taxable_value_similarity
                val_match = True
            elif pct_diff <= self.config.amount_tolerance_pct.tight:
                val_score = weights.taxable_value_similarity * 0.80
                val_match = True
            elif pct_diff <= self.config.amount_tolerance_pct.moderate:
                val_score = weights.taxable_value_similarity * 0.50
                val_match = True

        field_scores["taxable_value"] = round(val_score, 2)
        field_matches["taxable_value"] = val_match

        # 7. Tax Amount Similarity (Weight: 5)
        t1 = parse_decimal_safe(inv1.total_tax)
        t2 = parse_decimal_safe(inv2.total_tax)
        tax_score = 0.0
        tax_match = False
        if t1 > Decimal("0.00") and t2 > Decimal("0.00"):
            max_t = max(t1, t2)
            pct_t_diff = float((abs(t1 - t2) / max_t) * Decimal("100.00"))
            if pct_t_diff == 0.0:
                tax_score = weights.tax_amount_similarity
                tax_match = True
            elif pct_t_diff <= self.config.amount_tolerance_pct.tight:
                tax_score = weights.tax_amount_similarity * 0.80
                tax_match = True
            elif pct_t_diff <= self.config.amount_tolerance_pct.moderate:
                tax_score = weights.tax_amount_similarity * 0.50
                tax_match = True

        field_scores["tax_amount"] = round(tax_score, 2)
        field_matches["tax_amount"] = tax_match

        # Aggregate raw score
        total_score = sum(field_scores.values())

        # =====================================================================
        # False Positive Controls (Section 10)
        # =====================================================================
        is_recurring = False

        # Control A: Recurring Monthly Invoices (e.g. 25-35 days apart)
        # If invoice numbers differ substantially, identical values alone are recurring
        if (
            self.config.recurring_protection.enabled
            and days_diff is not None
            and self.config.recurring_protection.min_days_separation <= days_diff <= self.config.recurring_protection.max_days_separation
            and num_sim <= self.config.recurring_protection.number_similarity_ceiling
        ):
            is_recurring = True
            # Cap score below duplicate threshold
            total_score = min(total_score, 45.0)

        # Control B: Strong Invoice Identifier Dominance
        # If invoice numbers differ significantly (< 0.40 similarity), identical amounts
        # must NOT flag as a duplicate
        if num_sim < 0.40 and not is_recurring:
            total_score = min(total_score, 50.0)

        # Control C: Different Suppliers / Entities
        # Two completely distinct suppliers/counterparties cannot issue duplicates of each other
        if sup1 and sup2 and not field_matches["supplier_gstin"] and sup1 != "INTERNAL_SELLER" and sup2 != "INTERNAL_SELLER":
            total_score = min(total_score, 40.0)
        if buy1 and buy2 and not field_matches["buyer_gstin"] and buy1 != "INTERNAL_BUYER" and buy2 != "INTERNAL_BUYER":
            total_score = min(total_score, 40.0)

        # 8. Determine match type & confidence
        if total_score >= thresholds.exact_match:
            match_type = DuplicateMatchType.EXACT_DUPLICATE
            conf = IntelligenceConfidence.HIGH
        elif total_score >= thresholds.high_confidence_near:
            match_type = DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE
            conf = IntelligenceConfidence.HIGH
        elif total_score >= thresholds.possible_duplicate:
            match_type = DuplicateMatchType.POSSIBLE_DUPLICATE
            conf = IntelligenceConfidence.MEDIUM
        else:
            match_type = DuplicateMatchType.NO_DUPLICATE
            conf = IntelligenceConfidence.LOW

        evidence = {
            "source_invoice": inv1.invoice_id,
            "matched_invoice": inv2.invoice_id,
            "supplier_gstin_match": field_matches["supplier_gstin"],
            "buyer_gstin_match": field_matches["buyer_gstin"],
            "invoice_number_similarity": f"{num_sim * 100:.1f}%",
            "date_difference_days": days_diff,
            "taxable_value_source": f"INR {v1:,.2f}",
            "taxable_value_matched": f"INR {v2:,.2f}",
            "is_recurring_legitimate": is_recurring,
            "field_scores": field_scores,
            "rationalization": (
                "Legitimate recurring transaction pattern identified."
                if is_recurring
                else f"Combined structured similarity score of {total_score:.1f}/100.0."
            ),
        }

        return DuplicateCandidate(
            source_invoice_id=inv1.invoice_id,
            matched_invoice_id=inv2.invoice_id,
            match_type=match_type,
            similarity_score=round(total_score, 2),
            confidence=conf,
            field_matches=field_matches,
            field_scores=field_scores,
            evidence=evidence,
            is_recurring_legitimate=is_recurring,
        )

    def detect_near(self, invoices: List[Invoice]) -> List[DuplicateCandidate]:
        """
        Detect near-duplicate candidates across an invoice batch using indexing blocks.
        Blocks invoices by (supplier_gstin) or counterparty to optimize comparison.
        """
        from collections import defaultdict
        blocks: Dict[str, List[Invoice]] = defaultdict(list)

        for inv in invoices:
            sup, _ = extract_parties(inv)
            block_key = sup or getattr(inv, "counterparty_name", "UNKNOWN")
            blocks[block_key].append(inv)

        candidates: List[DuplicateCandidate] = []
        for block_key, group in blocks.items():
            n = len(group)
            if n < 2:
                continue
            for i in range(n):
                for j in range(i + 1, n):
                    cand = self.compare_pair(group[i], group[j])
                    if cand.match_type in (
                        DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE,
                        DuplicateMatchType.POSSIBLE_DUPLICATE,
                    ):
                        candidates.append(cand)

        return candidates
