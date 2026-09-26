"""
app.agent.ai.session
====================
Session Management & Multi-Turn Investigation Context Subsystem for UC15 (Sprint 12.4).
Provides thread-safe session tracking, accumulated evidence retention, active entity focus,
and implicit context resolution across multi-turn investigation queries.
Architected behind an abstract repository interface (BaseSessionRepository) for future S14 PostgreSQL migration.
"""

from __future__ import annotations

import os
import re
import threading
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.agent.ai.models import InvestigationIntentEnum
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

_session_manager: Optional[SessionManager] = None



class EntityFocus(BaseModel):
    """Tracks currently active entity context within a multi-turn investigation session."""
    invoice_id: Optional[str] = Field(None, description="Active invoice number (e.g. INV-8000001).")
    counterparty_gstin: Optional[str] = Field(None, description="Active vendor/counterparty GSTIN.")
    counterparty_name: Optional[str] = Field(None, description="Active vendor name (e.g. Tata Motors).")
    hsn_code: Optional[str] = Field(None, description="Active HSN/SAC code.")
    rule_category: Optional[str] = Field(None, description="Active compliance rule category (e.g. ITC, PLACE_OF_SUPPLY).")
    active_period: Optional[str] = Field(None, description="Active tax filing period.")
    risk_level: Optional[str] = Field(None, description="Active entity risk level.")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Focus tracking confidence score.")

    def update(self, **kwargs) -> None:
        """Update focus attributes if non-empty value provided."""
        for k, v in kwargs.items():
            if v and hasattr(self, k):
                setattr(self, k, v)

    def summary_string(self) -> str:
        """Render readable entity focus pill text."""
        parts = []
        if self.invoice_id:
            parts.append(f"Invoice: {self.invoice_id}")
        if self.counterparty_name or self.counterparty_gstin:
            parts.append(f"Vendor: {self.counterparty_name or self.counterparty_gstin}")
        if self.hsn_code:
            parts.append(f"HSN: {self.hsn_code}")
        if self.risk_level:
            parts.append(f"Risk: {self.risk_level}")
        return " | ".join(parts) if parts else "Portfolio Scope (No specific entity focused)"


class InvestigationTurn(BaseModel):
    """Represents a single turn in a multi-turn investigation conversation."""
    turn_index: int = Field(..., ge=1, description="Sequential turn index.")
    user_query: str = Field(..., description="Raw user query string.")
    resolved_query: str = Field(..., description="Query string after entity context resolution.")
    intent: str = Field(..., description="Detected investigation intent value.")
    tools_used: List[str] = Field(default_factory=list, description="Tools executed in this turn.")
    findings: List[Dict[str, Any]] = Field(default_factory=list, description="Deterministic findings produced in this turn.")
    regulatory_knowledge: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved regulatory evidence items.")
    synthesized_answer: str = Field(..., description="Final synthesized narrative answer.")
    confidence: str = Field("HIGH", description="Confidence rating.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO timestamp.",
    )


class InvestigationSession(BaseModel):
    """Domain model tracking a persistent multi-turn investigation workspace session."""
    session_id: str = Field(
        default_factory=lambda: f"SESS-{uuid.uuid4().hex[:8].upper()}",
        description="Unique session identifier.",
    )
    status: str = Field("ACTIVE", description="Session status: ACTIVE, COMPLETED, ARCHIVED.")
    turns: List[InvestigationTurn] = Field(default_factory=list, description="Ordered conversation turns.")
    accumulated_findings: List[Dict[str, Any]] = Field(default_factory=list, description="All deterministic findings across turns.")
    accumulated_regulatory_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="All regulatory evidence chunks across turns.")
    accumulated_contradictions: List[str] = Field(default_factory=list, description="All evidence contradictions detected.")
    entity_focus: EntityFocus = Field(default_factory=EntityFocus, description="Currently active entity focus.")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_turn(self, turn: InvestigationTurn) -> None:
        """Append turn and update accumulated findings/evidence and timestamp."""
        self.turns.append(turn)

        # Deduplicate and accumulate deterministic findings
        existing_keys = {f.get("source", "") + str(f.get("type", "")) for f in self.accumulated_findings}
        for f in turn.findings:
            key = f.get("source", "") + str(f.get("type", ""))
            if key not in existing_keys:
                self.accumulated_findings.append(f)
                existing_keys.add(key)

        # Deduplicate and accumulate regulatory evidence
        existing_chunks = {ev.get("chunk", {}).get("id") or ev.get("provenance", {}).get("chunk_id") or str(ev) for ev in self.accumulated_regulatory_evidence}
        for ev in turn.regulatory_knowledge:
            cid = ev.get("chunk", {}).get("id") or ev.get("provenance", {}).get("chunk_id") or str(ev)
            if cid and cid not in existing_chunks:
                self.accumulated_regulatory_evidence.append(ev)
                existing_chunks.add(cid)

        self.updated_at = datetime.now(timezone.utc).isoformat()


class BaseSessionRepository(ABC):
    """Abstract Repository interface for Investigation Sessions (enables S14 PostgreSQL swap)."""

    @abstractmethod
    def save_session(self, session: InvestigationSession) -> None:
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[InvestigationSession]:
        pass

    @abstractmethod
    def list_sessions(self) -> List[InvestigationSession]:
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        pass


class InMemorySessionRepository(BaseSessionRepository):
    """Thread-safe in-memory session repository implementation."""

    def __init__(self) -> None:
        self._sessions: Dict[str, InvestigationSession] = {}
        self._lock = threading.RLock()

    def save_session(self, session: InvestigationSession) -> None:
        with self._lock:
            self._sessions[session.session_id] = session

    def get_session(self, session_id: str) -> Optional[InvestigationSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> List[InvestigationSession]:
        with self._lock:
            return list(self._sessions.values())

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False


class SessionManager:
    """
    High-level Session Manager facade for UC15 multi-turn investigations.
    Handles session creation, implicit entity context resolution, turn recording,
    and entity focus updates.
    """

    def __init__(self, repository: Optional[BaseSessionRepository] = None) -> None:
        self.repository = repository or InMemorySessionRepository()

    def create_session(self, initial_focus: Optional[EntityFocus] = None) -> InvestigationSession:
        """Create and persist a new investigation workspace session."""
        sess = InvestigationSession(entity_focus=initial_focus or EntityFocus())
        self.repository.save_session(sess)
        logger.info(f"Created new investigation session: '{sess.session_id}'")
        return sess

    def get_session(self, session_id: str) -> Optional[InvestigationSession]:
        return self.repository.get_session(session_id)

    def resolve_query_context(
        self,
        session: InvestigationSession,
        user_query: str,
        explicit_invoice_id: Optional[str] = None,
        explicit_vendor_gstin: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Resolve implicit references ('this invoice', 'why is it non-compliant?', 'that vendor')
        against the active entity focus of the session.
        Returns (resolved_query, extracted_params).
        """
        params: Dict[str, Any] = {}
        clean_query = user_query.strip()
        resolved = clean_query

        # 1. Check for explicit invoice ID in query (e.g. INV-8000001 or INV-2026-CLEAN-AP-01)
        inv_match = re.search(r"\b(INV-[A-Z0-9-]+|\bINV\d+)\b", clean_query, re.IGNORECASE)
        if inv_match:
            inv_id = inv_match.group(1).upper()
            params["invoice_id"] = inv_id
            session.entity_focus.update(invoice_id=inv_id)
        elif explicit_invoice_id:
            params["invoice_id"] = explicit_invoice_id
            session.entity_focus.update(invoice_id=explicit_invoice_id)
        elif session.entity_focus.invoice_id:
            # Check for implicit pronouns
            implicit_triggers = ["this invoice", "that invoice", "why is it", "it is", "its risk", "its exposure", "this issue", "the invoice"]
            if any(tr in clean_query.lower() for tr in implicit_triggers) or not inv_match:
                params["invoice_id"] = session.entity_focus.invoice_id
                resolved = f"{clean_query} for invoice {session.entity_focus.invoice_id}"

        # 2. Check for GSTIN in query
        gstin_match = re.search(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b", clean_query)
        if gstin_match:
            gstin = gstin_match.group(0)
            params["counterparty_gstin"] = gstin
            session.entity_focus.update(counterparty_gstin=gstin)
        elif explicit_vendor_gstin:
            params["counterparty_gstin"] = explicit_vendor_gstin
            session.entity_focus.update(counterparty_gstin=explicit_vendor_gstin)
        elif session.entity_focus.counterparty_gstin:
            if "vendor" in clean_query.lower() or "supplier" in clean_query.lower() or "counterparty" in clean_query.lower():
                params["counterparty_gstin"] = session.entity_focus.counterparty_gstin

        # 3. Check for HSN code in query
        hsn_match = re.search(r"\bHSN\s*(\d{4,8})\b|\b(\d{4,8})\b", clean_query, re.IGNORECASE)
        if hsn_match:
            hsn = hsn_match.group(1) or hsn_match.group(2)
            if len(hsn) in [4, 6, 8]:
                params["hsn_code"] = hsn
                session.entity_focus.update(hsn_code=hsn)

        logger.info(f"Resolved query context for session '{session.session_id}': '{resolved}' (Params: {params})")
        return resolved, params

    def record_turn(
        self,
        session_id: str,
        user_query: str,
        resolved_query: str,
        intent: str,
        tools_used: List[str],
        findings: List[Dict[str, Any]],
        regulatory_knowledge: List[Dict[str, Any]],
        synthesized_answer: str,
        confidence: str = "HIGH",
    ) -> InvestigationSession:
        """Record a completed investigation turn in session and persist."""
        sess = self.get_session(session_id)
        if not sess:
            sess = self.create_session()

        turn_idx = len(sess.turns) + 1
        turn = InvestigationTurn(
            turn_index=turn_idx,
            user_query=user_query,
            resolved_query=resolved_query,
            intent=intent,
            tools_used=tools_used,
            findings=findings,
            regulatory_knowledge=regulatory_knowledge,
            synthesized_answer=synthesized_answer,
            confidence=confidence,
        )

        sess.add_turn(turn)
        self.repository.save_session(sess)
        logger.info(f"Recorded turn #{turn_idx} for session '{session_id}' (Total accumulated findings: {len(sess.accumulated_findings)})")
        return sess

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions summary."""
        sessions = self.repository.list_sessions()
        return [
            {
                "session_id": s.session_id,
                "status": s.status,
                "turn_count": len(s.turns),
                "entity_focus": s.entity_focus.summary_string(),
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in sessions
        ]

    def delete_session(self, session_id: str) -> bool:
        return self.repository.delete_session(session_id)


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        from app.db.connection import is_db_configured
        if is_db_configured():
            from app.agent.ai.sqlalchemy_session_repository import SQLAlchemySessionRepository
            repo = SQLAlchemySessionRepository()
        else:
            repo = InMemorySessionRepository()
        _session_manager = SessionManager(repository=repo)
    return _session_manager


def reset_session_manager() -> None:
    global _session_manager
    _session_manager = None

