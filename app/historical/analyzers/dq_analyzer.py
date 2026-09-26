"""
UC15 GST Compliance Agent — Data Quality History Analyzer (Sprint 5)
Analyzes recurring ingestion defects, missing fields, and structural data anomalies.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.historical.config.historical_config import HistoricalConfig, default_historical_config
from app.historical.models.data_quality import DataQualityPattern
from app.historical.models.period import PeriodMetrics
from app.historical.models.record import HistoricalRecord


class DataQualityAnalyzer:
    """
    Identifies repeated data-quality problems across transactions, vendors, and periods.
    Ensures data defects are isolated from statutory non-compliance.
    """

    def __init__(self, config: Optional[HistoricalConfig] = None) -> None:
        self.config = config or default_historical_config

    def analyze(
        self,
        records: List[HistoricalRecord],
        periods: List[PeriodMetrics],
    ) -> List[DataQualityPattern]:
        """
        Scan records for data quality defects and classify patterns.
        """
        if not records:
            return []

        # Map findings: issue_key -> list of records
        dq_occurrences: Dict[str, List[HistoricalRecord]] = defaultdict(list)
        counterparty_dq: Dict[str, Dict[str, List[HistoricalRecord]]] = defaultdict(lambda: defaultdict(list))

        for r in records:
            # 1. Inspect explicit data_quality_findings
            for dq_msg in r.data_quality_findings:
                issue_type = self._normalize_issue_type(dq_msg)
                dq_occurrences[issue_type].append(r)
                c_id = r.counterparty_gstin or r.counterparty_name or "UNKNOWN"
                counterparty_dq[c_id][issue_type].append(r)

            # 2. Inspect implicit missing structural fields
            if not r.invoice_id or r.invoice_id.strip() == "":
                dq_occurrences["MISSING_INVOICE_ID"].append(r)
            if not r.place_of_supply or r.place_of_supply.strip() == "":
                dq_occurrences["MISSING_PLACE_OF_SUPPLY"].append(r)
            if not r.counterparty_gstin or r.counterparty_gstin.strip() == "":
                dq_occurrences["MISSING_COUNTERPARTY_GSTIN"].append(r)
            if not r.hsn_code or r.hsn_code.strip() == "":
                dq_occurrences["MISSING_HSN_CODE"].append(r)

        patterns: List[DataQualityPattern] = []
        total_records = len(records)

        # 1. Global / Systemic Data Quality Patterns
        for issue_type, affected_recs in sorted(dq_occurrences.items()):
            # Deduplicate by invoice_id
            unique_recs = {r.invoice_id: r for r in affected_recs}.values()
            cnt = len(unique_recs)
            if cnt == 0:
                continue

            periods_seen: set[str] = set()
            for r in unique_recs:
                for p in periods:
                    if p.start_date <= r.invoice_date <= p.end_date:
                        periods_seen.add(p.period_key)
                        break

            is_recurring = cnt >= self.config.dq_min_occurrences
            desc = self._get_issue_description(issue_type)
            ev = f"Data quality defect '{issue_type}' observed in {cnt} invoice(s) across {len(periods_seen)} period(s)."

            pat = DataQualityPattern(
                pattern_id=f"PAT-DQ-{issue_type}",
                issue_type=issue_type,
                description=desc,
                counterparty_id=None,
                occurrence_count=cnt,
                total_invoices_evaluated=total_records,
                affected_invoices=sorted([r.invoice_id for r in unique_recs]),
                periods_observed=sorted(list(periods_seen)),
                is_recurring=is_recurring,
                evidence=ev,
            )
            pat.calculate_rate()
            patterns.append(pat)

        # 2. Counterparty-specific high DQ defect patterns
        for c_id, issue_map in sorted(counterparty_dq.items()):
            cp_total = sum(1 for r in records if (r.counterparty_gstin or r.counterparty_name) == c_id)
            if cp_total == 0:
                continue

            for issue_type, affected_recs in issue_map.items():
                unique_recs = {r.invoice_id: r for r in affected_recs}.values()
                cnt = len(unique_recs)
                ratio = cnt / cp_total

                if cnt >= self.config.dq_min_occurrences and ratio >= self.config.dq_counterparty_affected_ratio:
                    periods_seen = set()
                    for r in unique_recs:
                        for p in periods:
                            if p.start_date <= r.invoice_date <= p.end_date:
                                periods_seen.add(p.period_key)
                                break

                    pat = DataQualityPattern(
                        pattern_id=f"PAT-DQ-{c_id[:10]}-{issue_type}",
                        issue_type=f"{issue_type}_BY_COUNTERPARTY",
                        description=f"{round(ratio * 100.0, 1)}% of invoices from counterparty '{c_id}' have {issue_type.lower()}.",
                        counterparty_id=c_id,
                        occurrence_count=cnt,
                        total_invoices_evaluated=cp_total,
                        affected_invoices=sorted([r.invoice_id for r in unique_recs]),
                        periods_observed=sorted(list(periods_seen)),
                        is_recurring=True,
                        evidence=f"Counterparty '{c_id}' has {cnt}/{cp_total} invoices ({round(ratio * 100.0, 1)}%) affected by {issue_type}.",
                    )
                    pat.calculate_rate()
                    patterns.append(pat)

        # Sort: recurring first, then occurrence_count desc
        return sorted(patterns, key=lambda p: (not p.is_recurring, -p.occurrence_count))

    def _normalize_issue_type(self, msg: str) -> str:
        msg_lower = msg.lower()
        if "gstin" in msg_lower:
            return "INVALID_GSTIN_FORMAT"
        elif "date" in msg_lower:
            return "INVALID_INVOICE_DATE"
        elif "state" in msg_lower or "place of supply" in msg_lower:
            return "MISSING_STATE_INFO"
        elif "hsn" in msg_lower:
            return "MISSING_OR_MALFORMED_HSN"
        elif "rate" in msg_lower:
            return "INVALID_TAX_RATE_SPECIFICATION"
        else:
            return "MALFORMED_DATA_FIELD"

    def _get_issue_description(self, issue_type: str) -> str:
        descriptions = {
            "INVALID_GSTIN_FORMAT": "Malformed or unparseable counterparty GSTIN format.",
            "INVALID_INVOICE_DATE": "Missing, unparseable, or illogical transaction date.",
            "MISSING_STATE_INFO": "Missing supplier, buyer, or place of supply state identifier.",
            "MISSING_PLACE_OF_SUPPLY": "Invoice omitted required statutory Place of Supply declaration.",
            "MISSING_COUNTERPARTY_GSTIN": "Missing counterparty GST identification number.",
            "MISSING_HSN_CODE": "Missing mandatory HSN/SAC classification code.",
            "MISSING_INVOICE_ID": "Missing or blank canonical invoice identification number.",
            "MALFORMED_DATA_FIELD": "Defective, non-standard, or unparseable invoice field data.",
        }
        return descriptions.get(issue_type, f"Recurring data quality issue: {issue_type}")
