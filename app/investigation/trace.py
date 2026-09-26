"""
app.investigation.trace
=======================
Operational Execution Trace Tracker for UC15 (Sprint 18).
Captures structured operational step execution events without exposing private LLM model chain-of-thought.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class TraceEvent(BaseModel):
    """Structured operational trace event item."""
    trace_id: str = Field(
        default_factory=lambda: f"TRC-{uuid.uuid4().hex[:8].upper()}",
        description="Unique trace event ID.",
    )
    investigation_id: str = Field(..., description="Parent investigation ID.")
    case_id: str = Field(..., description="Target case ID.")
    step_id: str = Field(..., description="Step ID.")
    tool_name: str = Field(..., description="Executed tool/subsystem name.")
    status: str = Field("SUCCESS", description="Step status: SUCCESS, FAILED, TIMEOUT, BLOCKED, SKIPPED.")
    duration_seconds: float = Field(0.0, ge=0.0, description="Step duration.")
    output_summary: str = Field("", description="Condensed output description.")
    error: Optional[str] = Field(None, description="Error message if failed.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )


class InvestigationTraceTracker:
    """In-memory & persistent operational trace manager."""

    _TRACES: Dict[str, List[TraceEvent]] = {}

    @classmethod
    def record_event(
        cls,
        investigation_id: str,
        case_id: str,
        step_id: str,
        tool_name: str,
        status: str,
        duration_seconds: float = 0.0,
        output_summary: str = "",
        error: Optional[str] = None,
    ) -> TraceEvent:
        event = TraceEvent(
            investigation_id=investigation_id,
            case_id=case_id,
            step_id=step_id,
            tool_name=tool_name,
            status=status,
            duration_seconds=duration_seconds,
            output_summary=output_summary,
            error=error,
        )
        if investigation_id not in cls._TRACES:
            cls._TRACES[investigation_id] = []
        cls._TRACES[investigation_id].append(event)
        logger.info(f"Recorded trace event for investigation '{investigation_id}', step '{step_id}' ({tool_name}: {status}).")
        return event

    @classmethod
    def get_trace(cls, investigation_id: str) -> List[TraceEvent]:
        return cls._TRACES.get(investigation_id, [])

    @classmethod
    def clear_trace(cls, investigation_id: str) -> None:
        cls._TRACES.pop(investigation_id, None)
