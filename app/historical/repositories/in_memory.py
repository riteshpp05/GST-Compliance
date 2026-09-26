"""
UC15 GST Compliance Agent — In-Memory Historical Repository (Sprint 5)
Provides thread-safe, fast in-memory indexing of HistoricalRecords.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Set

from app.historical.models.record import HistoricalRecord
class InMemoryHistoricalRepository:
    """
    High-performance in-memory repository for historical records.
    Maintains primary key index on invoice_id and inverted indexes on counterparty and failed rules.
    """

    def __init__(self) -> None:
        self._records: Dict[str, HistoricalRecord] = {}
        # Inverted index: counterparty_id (clean lowercase) -> set of invoice_ids
        self._counterparty_idx: Dict[str, Set[str]] = defaultdict(set)
        # Inverted index: rule_id -> set of invoice_ids
        self._rule_idx: Dict[str, Set[str]] = defaultdict(set)

    def add(self, record: HistoricalRecord) -> None:
        """Store a single record and update indices."""
        self._records[record.invoice_id] = record

        # Index counterparty
        if record.counterparty_gstin:
            self._counterparty_idx[record.counterparty_gstin.strip().upper()].add(record.invoice_id)
        if record.counterparty_name:
            self._counterparty_idx[record.counterparty_name.strip().lower()].add(record.invoice_id)

        # Index failed rules
        for rid in record.failed_rule_ids:
            self._rule_idx[rid].add(record.invoice_id)

    def add_batch(self, records: List[HistoricalRecord]) -> None:
        """Store multiple records."""
        for rec in records:
            self.add(rec)

    def get_by_invoice_id(self, invoice_id: str) -> Optional[HistoricalRecord]:
        return self._records.get(invoice_id)

    def list_all(self) -> List[HistoricalRecord]:
        """Return all records sorted chronologically by invoice_date, then invoice_id."""
        return sorted(self._records.values(), key=lambda r: (r.invoice_date or date(2023, 1, 1), r.invoice_id))

    def query_by_date_range(self, start_date: date, end_date: date) -> List[HistoricalRecord]:
        """Return records whose invoice_date falls in [start_date, end_date]."""
        return [
            r for r in self.list_all()
            if r.invoice_date and (start_date <= r.invoice_date <= end_date)
        ]

    def query_by_counterparty(self, counterparty_id: str) -> List[HistoricalRecord]:
        """Query by counterparty GSTIN or name."""
        clean_id = counterparty_id.strip()
        inv_ids = (
            self._counterparty_idx.get(clean_id.upper(), set()) |
            self._counterparty_idx.get(clean_id.lower(), set())
        )
        return [self._records[iid] for iid in inv_ids if iid in self._records]

    def query_by_rule_failure(self, rule_id: str) -> List[HistoricalRecord]:
        """Query records that failed a specific rule."""
        inv_ids = self._rule_idx.get(rule_id, set())
        return [self._records[iid] for iid in inv_ids if iid in self._records]

    def clear(self) -> None:
        self._records.clear()
        self._counterparty_idx.clear()
        self._rule_idx.clear()

    def count(self) -> int:
        return len(self._records)

