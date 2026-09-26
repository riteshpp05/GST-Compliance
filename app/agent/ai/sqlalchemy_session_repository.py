"""
app.agent.ai.sqlalchemy_session_repository
===========================================
Relational SQLAlchemy Repository implementation for Investigation Sessions (Sprint 14).
Supports PostgreSQL and SQLite backends while implementing BaseSessionRepository interface.
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from app.agent.ai.models import InvestigationIntentEnum
from app.agent.ai.session import (
    BaseSessionRepository,
    EntityFocus,
    InvestigationSession,
    InvestigationTurn,
)
from app.db.connection import db_session_scope, get_db_session
from app.db.models import SessionORM, TurnORM
from app.db.serializer import dump_json_value, load_json_value
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLAlchemySessionRepository(BaseSessionRepository):
    """Relational Database Session Repository implementation using SQLAlchemy 2.0."""

    def save_session(self, session: InvestigationSession) -> None:
        """Upsert InvestigationSession domain model and its turns into relational database."""
        with db_session_scope() as db:
            existing = db.execute(
                select(SessionORM).where(SessionORM.session_id == session.session_id)
            ).scalar_one_or_none()

            focus_json = dump_json_value(session.entity_focus.model_dump() if session.entity_focus else {})
            findings_json = dump_json_value(session.accumulated_findings)
            reg_json = dump_json_value(session.accumulated_regulatory_evidence)

            if existing is None:
                orm_sess = SessionORM(
                    session_id=session.session_id,
                    status=session.status,
                    entity_focus_json=focus_json,
                    accumulated_findings_json=findings_json,
                    accumulated_regulatory_evidence_json=reg_json,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                )
                db.add(orm_sess)
            else:
                existing.status = session.status
                existing.entity_focus_json = focus_json
                existing.accumulated_findings_json = findings_json
                existing.accumulated_regulatory_evidence_json = reg_json
                existing.updated_at = session.updated_at
                orm_sess = existing

            # Synchronize turns
            db.flush()
            existing_turns = {
                t.turn_index: t for t in db.execute(
                    select(TurnORM).where(TurnORM.session_id == session.session_id)
                ).scalars().all()
            }

            for turn in session.turns:
                t_idx = turn.turn_index
                intent_str = turn.intent.value if hasattr(turn.intent, "value") else str(turn.intent)
                tools_json = dump_json_value(turn.tools_used)
                find_json = dump_json_value(turn.findings)
                reg_know_json = dump_json_value(turn.regulatory_knowledge)

                if t_idx in existing_turns:
                    t_orm = existing_turns[t_idx]
                    t_orm.user_query = turn.user_query
                    t_orm.resolved_query = turn.resolved_query
                    t_orm.intent = intent_str
                    t_orm.tools_used_json = tools_json
                    t_orm.findings_json = find_json
                    t_orm.regulatory_knowledge_json = reg_know_json
                    t_orm.synthesized_answer = turn.synthesized_answer
                    t_orm.confidence = turn.confidence
                    t_orm.timestamp = turn.timestamp
                else:
                    t_orm = TurnORM(
                        session_id=session.session_id,
                        turn_index=t_idx,
                        user_query=turn.user_query,
                        resolved_query=turn.resolved_query,
                        intent=intent_str,
                        tools_used_json=tools_json,
                        findings_json=find_json,
                        regulatory_knowledge_json=reg_know_json,
                        synthesized_answer=turn.synthesized_answer,
                        confidence=turn.confidence,
                        timestamp=turn.timestamp,
                    )
                    db.add(t_orm)

        logger.debug(f"Saved session '{session.session_id}' to relational repository ({len(session.turns)} turns)")

    def get_session(self, session_id: str) -> Optional[InvestigationSession]:
        """Retrieve InvestigationSession domain model from relational database."""
        db = get_db_session()
        try:
            orm_sess = db.execute(
                select(SessionORM)
                .options(joinedload(SessionORM.turns))
                .where(SessionORM.session_id == session_id)
            ).unique().scalar_one_or_none()

            if not orm_sess:
                return None

            focus_dict = load_json_value(orm_sess.entity_focus_json, default_factory=dict)
            focus_obj = EntityFocus(**focus_dict) if focus_dict else EntityFocus()

            acc_findings = load_json_value(orm_sess.accumulated_findings_json, default_factory=list)
            acc_reg = load_json_value(orm_sess.accumulated_regulatory_evidence_json, default_factory=list)

            turns: List[InvestigationTurn] = []
            sorted_turns = sorted(orm_sess.turns, key=lambda t: t.turn_index)
            for t_orm in sorted_turns:
                tools_list = load_json_value(t_orm.tools_used_json, default_factory=list)
                findings_list = load_json_value(t_orm.findings_json, default_factory=list)
                reg_list = load_json_value(t_orm.regulatory_knowledge_json, default_factory=list)

                turn_obj = InvestigationTurn(
                    turn_index=t_orm.turn_index,
                    user_query=t_orm.user_query,
                    resolved_query=t_orm.resolved_query,
                    intent=t_orm.intent,
                    tools_used=tools_list,
                    findings=findings_list,
                    regulatory_knowledge=reg_list,
                    synthesized_answer=t_orm.synthesized_answer,
                    confidence=t_orm.confidence,
                    timestamp=t_orm.timestamp,
                )
                turns.append(turn_obj)

            sess_obj = InvestigationSession(
                session_id=orm_sess.session_id,
                status=orm_sess.status,
                turns=turns,
                accumulated_findings=acc_findings,
                accumulated_regulatory_evidence=acc_reg,
                entity_focus=focus_obj,
                created_at=orm_sess.created_at,
                updated_at=orm_sess.updated_at,
            )
            return sess_obj
        finally:
            db.close()

    def list_sessions(self) -> List[InvestigationSession]:
        """List all InvestigationSessions."""
        db = get_db_session()
        try:
            orm_sessions = db.execute(
                select(SessionORM).options(joinedload(SessionORM.turns)).order_by(SessionORM.updated_at.desc())
            ).unique().scalars().all()

            results: List[InvestigationSession] = []
            for s_orm in orm_sessions:
                sess = self.get_session(s_orm.session_id)
                if sess:
                    results.append(sess)
            return results
        finally:
            db.close()

    def delete_session(self, session_id: str) -> bool:
        """Delete session and its associated turns."""
        with db_session_scope() as db:
            result = db.execute(delete(SessionORM).where(SessionORM.session_id == session_id))
            return result.rowcount > 0
