"""
app.intelligence.duplicate.fingerprint
======================================
Deterministic attribute normalization, identity fingerprinting, and string distance algorithms.
Provides reproducible hashing and distance metrics without third-party dependencies.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple, Union

from app.domain.models.invoice import Invoice
from app.intelligence.config.intelligence_config import DuplicateNormalizationConfig


def round_monetary(val: Decimal) -> Decimal:
    """Round to 2 decimal places using standard statutory ROUND_HALF_UP."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalize_invoice_number(
    invoice_number: Optional[Union[str, int, float]],
    remove_separators: bool = True,
) -> str:
    """
    Normalize invoice number for deterministic identity matching.
    Strips whitespace, converts to uppercase, and optionally removes harmless separators (-, /, space).
    """
    if invoice_number is None:
        return ""
    s = str(invoice_number).strip().upper()
    if not s:
        return ""
    if remove_separators:
        s = re.sub(r"[\s\-_/\\.,#]+", "", s)
    return s


def normalize_gstin(gstin: Optional[str]) -> str:
    """Normalize GSTIN (strip whitespace and uppercase)."""
    if not gstin:
        return ""
    return str(gstin).strip().upper()


def normalize_date(dt: Any) -> Optional[str]:
    """Normalize date object or string into YYYY-MM-DD ISO format."""
    if dt is None:
        return None
    if isinstance(dt, date):
        return dt.isoformat()
    if isinstance(dt, datetime):
        return dt.date().isoformat()
    s = str(dt).strip()
    if not s:
        return None
    # Parse potential formats
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return s[:10]


def parse_decimal_safe(val: Any) -> Decimal:
    """Safely convert any numeric value or string to Decimal rounded to 2 decimal places."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return round_monetary(val)
    try:
        s = str(val).replace(",", "").strip()
        if not s:
            return Decimal("0.00")
        return round_monetary(Decimal(s))
    except Exception:
        return Decimal("0.00")


def extract_parties(inv: Invoice) -> Tuple[str, str]:
    """
    Extract canonical (supplier_gstin, buyer_gstin) based on invoice direction.
    For AP (inward / purchases): supplier is seller/gstin, buyer is buyer_gstin.
    For AR (outward / sales): supplier is seller_gstin, buyer is buyer/gstin.
    """
    direction = (getattr(inv, "direction", "AP") or "AP").upper()
    counterparty_gstin = normalize_gstin(getattr(inv, "gstin", None) or getattr(inv, "counterparty_gstin", None))
    seller_gstin = normalize_gstin(getattr(inv, "seller_gstin", None))
    buyer_gstin = normalize_gstin(getattr(inv, "buyer_gstin", None))

    if direction == "AP":
        supplier = seller_gstin or counterparty_gstin
        buyer = buyer_gstin or getattr(inv, "recipient_gstin", "") or "INTERNAL_BUYER"
    else:
        supplier = seller_gstin or getattr(inv, "issuer_gstin", "") or "INTERNAL_SELLER"
        buyer = buyer_gstin or counterparty_gstin

    return supplier, buyer


def generate_exact_fingerprint(
    inv: Invoice,
    config: Optional[DuplicateNormalizationConfig] = None,
) -> Optional[str]:
    """
    Generate SHA-256 identity fingerprint for exact duplicate matching.
    Returns None if critical identity attributes are missing (causing NOT_EVALUATED).
    """
    remove_seps = config.remove_separators if config else True
    inv_no = normalize_invoice_number(inv.invoice_number, remove_separators=remove_seps)
    supplier_gstin, buyer_gstin = extract_parties(inv)
    inv_date = normalize_date(inv.invoice_date)
    taxable_val = parse_decimal_safe(inv.taxable_value)
    tax_amt = parse_decimal_safe(inv.total_tax)

    # Missing critical identity attributes
    if not inv_no or not supplier_gstin or not inv_date:
        return None

    # Canonical representation
    raw = f"{supplier_gstin}|{buyer_gstin}|{inv_no}|{inv_date}|{taxable_val:.2f}|{tax_amt:.2f}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def levenshtein_distance(s1: str, s2: str) -> int:
    """Pure Python Levenshtein edit distance calculation (zero dependencies)."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compute_string_similarity(s1: str, s2: str) -> float:
    """
    Computes hybrid string similarity (0.0 to 1.0) combining Levenshtein and SequenceMatcher.
    Deterministic, case-insensitive.
    """
    s1_clean = s1.strip().upper()
    s2_clean = s2.strip().upper()
    if s1_clean == s2_clean:
        return 1.0
    if not s1_clean or not s2_clean:
        return 0.0

    max_len = max(len(s1_clean), len(s2_clean))
    dist = levenshtein_distance(s1_clean, s2_clean)
    lev_ratio = 1.0 - (dist / max_len)

    seq_ratio = difflib.SequenceMatcher(None, s1_clean, s2_clean).ratio()

    # Blend: 60% Levenshtein, 40% SequenceMatcher
    return round((0.6 * lev_ratio) + (0.4 * seq_ratio), 4)
