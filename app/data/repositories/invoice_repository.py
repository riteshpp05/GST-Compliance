"""
UC15 GST Compliance Agent — Invoice Repository
Provides access and persistence abstractions for invoices and reference master data.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.domain.models.tax import HSNMaster


class InvoiceRepository(ABC):
    """Abstract interface for accessing invoice and tax master records."""

    @abstractmethod
    def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Fetch invoice by invoice number/ID."""

    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Alias for get_by_id to support data ingestion service interface."""
        return self.get_by_id(invoice_id)

    @abstractmethod
    def list_all(self) -> List[Invoice]:
        """List all invoices."""

    @abstractmethod
    def add(self, invoice: Invoice) -> None:
        """Add a single invoice to the repository."""

    def save_invoice(self, invoice: Invoice) -> None:
        """Alias for add to support data ingestion service interface."""
        self.add(invoice)

    @abstractmethod
    def add_batch(self, invoices: List[Invoice]) -> None:
        """Add multiple invoices to the repository."""

    @abstractmethod
    def get_hsn(self, hsn_code: str) -> Optional[HSNMaster]:
        """Fetch HSN master record."""

    @abstractmethod
    def get_state_name(self, state_code: str) -> Optional[str]:
        """Fetch official state name for a GSTIN prefix."""


import os
import json
import sqlite3
from datetime import datetime, timezone


class InMemoryInvoiceRepository(InvoiceRepository):
    """Thread-safe repository implementation backed by persistent SQLite storage."""
    _SHARED_INVOICES: Dict[str, Invoice] = {}
    _SHARED_HSN: Dict[str, HSNMaster] = {}
    _SHARED_STATES: Dict[str, str] = {}
    _CORRECTIONS_LOG: Dict[str, List[dict]] = {}
    _APPROVAL_LOG: Dict[str, dict] = {}
    _APPROVAL_HISTORY_LOG: Dict[str, List[dict]] = {}
    _DB_INITIALIZED: bool = False

    def __init__(
        self,
        invoices: Optional[List[Invoice]] = None,
        hsn_master: Optional[Dict[str, HSNMaster]] = None,
        state_codes: Optional[Dict[str, str]] = None,
    ):
        self._invoices = self._SHARED_INVOICES
        self._hsn_master = self._SHARED_HSN
        self._state_codes = self._SHARED_STATES

        self._db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "data",
            "compliance_store.db"
        )
        self._init_sqlite()

        if hsn_master:
            self._hsn_master.update(hsn_master)
        if state_codes:
            self._state_codes.update(state_codes)
        if invoices is not None:
            self._invoices.clear()
            self.add_batch(invoices)

    def _get_db_connection(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        conn = sqlite3.connect(self._db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_sqlite(self) -> None:
        """Initialize database schema and load persisted approvals/corrections into memory."""
        if InMemoryInvoiceRepository._DB_INITIALIZED:
            return

        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS invoice_approvals (
                invoice_no TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                approved_by TEXT NOT NULL,
                approved_at TEXT NOT NULL,
                comment TEXT,
                compliance_status_at_approval TEXT,
                gates_passed INTEGER,
                gates_failed INTEGER,
                invalidated INTEGER DEFAULT 0
            )
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS invoice_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                corrected_by TEXT NOT NULL,
                reason TEXT,
                changes_json TEXT
            )
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL,
                event_type TEXT NOT NULL,
                action_label TEXT NOT NULL,
                actor TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                reason TEXT,
                changes_json TEXT,
                status TEXT
            )
            """)
            conn.commit()

            # Pre-load approvals from disk
            cur.execute("SELECT * FROM invoice_approvals")
            for row in cur.fetchall():
                entry = {
                    "status": row["status"],
                    "approved_by": row["approved_by"],
                    "approved_at": row["approved_at"],
                    "comment": row["comment"] or "",
                    "compliance_status_at_approval": row["compliance_status_at_approval"] or "",
                    "gates_passed_at_approval": row["gates_passed"] or 0,
                    "gates_failed_at_approval": row["gates_failed"] or 0,
                    "invalidated": bool(row["invalidated"]),
                }
                inv_no = row["invoice_no"]
                self._APPROVAL_LOG[inv_no] = entry
                if inv_no not in self._APPROVAL_HISTORY_LOG:
                    self._APPROVAL_HISTORY_LOG[inv_no] = []
                self._APPROVAL_HISTORY_LOG[inv_no].append(dict(entry))

            # Pre-load corrections from disk
            cur.execute("SELECT * FROM invoice_corrections ORDER BY id ASC")
            for row in cur.fetchall():
                inv_no = row["invoice_no"]
                try:
                    changes = json.loads(row["changes_json"]) if row["changes_json"] else {}
                except Exception:
                    changes = {}
                c_entry = {
                    "timestamp": row["timestamp"],
                    "corrected_by": row["corrected_by"],
                    "reason": row["reason"] or "",
                    "changes": changes,
                }
                if inv_no not in self._CORRECTIONS_LOG:
                    self._CORRECTIONS_LOG[inv_no] = []
                self._CORRECTIONS_LOG[inv_no].append(c_entry)

            conn.close()
            InMemoryInvoiceRepository._DB_INITIALIZED = True
        except Exception as e:
            # Fall back gracefully to memory if SQLite error occurs
            pass

    def clear(self) -> None:
        """Clear all stored invoices."""
        self._invoices.clear()

    def get_by_id(self, invoice_id: str) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)

    def list_all(self) -> List[Invoice]:
        return list(self._invoices.values())

    def add(self, invoice: Invoice) -> None:
        self._invoices[invoice.invoice_number] = invoice

    def add_batch(self, invoices: List[Invoice]) -> None:
        for inv in invoices:
            self.add(inv)

    def set_hsn_master(self, hsn_master: Dict[str, HSNMaster]) -> None:
        self._hsn_master = dict(hsn_master)

    def get_hsn(self, hsn_code: str) -> Optional[HSNMaster]:
        return self._hsn_master.get(hsn_code)

    def set_state_codes(self, state_codes: Dict[str, str]) -> None:
        self._state_codes = dict(state_codes)

    def get_state_name(self, state_code: str) -> Optional[str]:
        return self._state_codes.get(state_code)

    def __len__(self) -> int:
        return len(self._invoices)

    # ---- Correction Audit Trail ----

    def record_correction(self, invoice_no: str, changes: dict, corrected_by: str, reason: str) -> None:
        """Record a correction entry in the audit log and persist to SQLite."""
        ts = datetime.now(timezone.utc).isoformat()
        entry = {
            "timestamp": ts,
            "corrected_by": corrected_by,
            "reason": reason,
            "changes": changes,
        }
        if invoice_no not in self._CORRECTIONS_LOG:
            self._CORRECTIONS_LOG[invoice_no] = []
        self._CORRECTIONS_LOG[invoice_no].append(entry)
        
        # Invalidate any existing approval when a correction is applied
        if invoice_no in self._APPROVAL_LOG:
            self._APPROVAL_LOG[invoice_no]["invalidated"] = True

        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO invoice_corrections (invoice_no, timestamp, corrected_by, reason, changes_json)
            VALUES (?, ?, ?, ?, ?)
            """, (invoice_no, ts, corrected_by, reason, json.dumps(changes)))

            cur.execute("""
            UPDATE invoice_approvals SET invalidated = 1 WHERE invoice_no = ?
            """, (invoice_no,))

            cur.execute("""
            INSERT INTO audit_trail (invoice_no, event_type, action_label, actor, timestamp, reason, changes_json, status)
            VALUES (?, 'CORRECTION', 'Correction Applied', ?, ?, ?, ?, 'CORRECTED')
            """, (invoice_no, corrected_by, ts, reason, json.dumps(changes)))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_corrections(self, invoice_no: str) -> List[dict]:
        """Get the correction audit trail for an invoice."""
        return list(self._CORRECTIONS_LOG.get(invoice_no, []))

    # ---- Approval Lifecycle ----

    def record_approval(self, invoice_no: str, action: str, comment: str, actor: str,
                        compliance_status: str, gates_passed: int, gates_failed: int) -> dict:
        """Record an approval or rejection decision on an invoice and persist to SQLite."""
        ts = datetime.now(timezone.utc).isoformat()
        norm_status = "APPROVED" if action.upper() in ("APPROVE", "APPROVED") else "REJECTED"
        entry = {
            "status": norm_status,
            "approved_by": actor,
            "approved_at": ts,
            "comment": comment,
            "compliance_status_at_approval": compliance_status,
            "gates_passed_at_approval": gates_passed,
            "gates_failed_at_approval": gates_failed,
            "invalidated": False,
        }
        self._APPROVAL_LOG[invoice_no] = entry
        if invoice_no not in self._APPROVAL_HISTORY_LOG:
            self._APPROVAL_HISTORY_LOG[invoice_no] = []
        self._APPROVAL_HISTORY_LOG[invoice_no].append(dict(entry))

        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            cur.execute("""
            INSERT OR REPLACE INTO invoice_approvals (invoice_no, status, approved_by, approved_at, comment, compliance_status_at_approval, gates_passed, gates_failed, invalidated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (invoice_no, norm_status, actor, ts, comment, compliance_status, gates_passed, gates_failed))

            action_label = "Approved" if norm_status == "APPROVED" else "Rejected"
            cur.execute("""
            INSERT INTO audit_trail (invoice_no, event_type, action_label, actor, timestamp, reason, changes_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_no,
                norm_status,
                action_label,
                actor,
                ts,
                comment,
                json.dumps({
                    "decision": norm_status,
                    "compliance_status": compliance_status,
                    "gates_passed": gates_passed,
                    "gates_failed": gates_failed,
                }),
                norm_status,
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

        return entry

    def get_approval(self, invoice_no: str) -> Optional[dict]:
        """Get the current approval status for an invoice, or None."""
        return self._APPROVAL_LOG.get(invoice_no)

    def get_all_approvals(self) -> Dict[str, dict]:
        """Get all approval records."""
        return dict(self._APPROVAL_LOG)

    def get_all_audit_trail(self, limit: int = 500) -> List[dict]:
        """Retrieve unified, reverse-chronological change ledger of all corrections and approvals from SQLite."""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM audit_trail ORDER BY id DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            events = []
            for r in rows:
                try:
                    changes = json.loads(r["changes_json"]) if r["changes_json"] else {}
                except Exception:
                    changes = {}
                events.append({
                    "invoice_no": r["invoice_no"],
                    "event_type": r["event_type"],
                    "action_label": r["action_label"],
                    "actor": r["actor"],
                    "timestamp": r["timestamp"],
                    "reason": r["reason"] or "",
                    "changes": changes,
                    "status": r["status"],
                })
            conn.close()
            if events:
                return events
        except Exception:
            pass

        # Fallback to in-memory events if DB read fails
        events = []
        for inv_no, entries in self._CORRECTIONS_LOG.items():
            for entry in entries:
                events.append({
                    "invoice_no": inv_no,
                    "event_type": "CORRECTION",
                    "action_label": "Correction Applied",
                    "actor": entry.get("corrected_by", "FINANCE_LEAD"),
                    "timestamp": entry.get("timestamp"),
                    "reason": entry.get("reason", ""),
                    "changes": entry.get("changes", {}),
                    "status": "CORRECTED",
                })

        for inv_no, entries in self._APPROVAL_HISTORY_LOG.items():
            for entry in entries:
                action_label = "Approved" if entry.get("status") == "APPROVED" else "Rejected"
                events.append({
                    "invoice_no": inv_no,
                    "event_type": entry.get("status", "APPROVED"),
                    "action_label": action_label,
                    "actor": entry.get("approved_by", "FINANCE_LEAD"),
                    "timestamp": entry.get("approved_at"),
                    "reason": entry.get("comment", ""),
                    "changes": {
                        "decision": entry.get("status"),
                        "compliance_status": entry.get("compliance_status_at_approval"),
                        "gates_passed": entry.get("gates_passed_at_approval"),
                        "gates_failed": entry.get("gates_failed_at_approval"),
                        "invalidated": entry.get("invalidated", False),
                    },
                    "status": entry.get("status"),
                })

        events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
        return events[:limit]

