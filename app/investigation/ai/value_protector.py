"""
UC15 GST Compliance Agent — Deterministic Value Protector (Sprint 23)
Enforces read-only protection of financial amounts, tax rates, exposure classifications,
and statutory rule verdicts. Replaces conflicting AI values with authoritative engine figures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.investigation.ai.context_builder import ControlledInvestigationContext


@dataclass
class ValueConflictLog:
    field_name: str
    ai_value: Any
    deterministic_value: Any
    resolution: str = "DETERMINISTIC_VALUE_PRESERVED"
    action_taken: str = "AI_VALUE_REJECTED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "ai_value": self.ai_value,
            "deterministic_value": self.deterministic_value,
            "resolution": self.resolution,
            "action_taken": self.action_taken,
        }


@dataclass
class ValueProtectionResult:
    case_id: str
    is_protected: bool = True
    has_conflicts: bool = False
    conflict_logs: List[ValueConflictLog] = field(default_factory=list)
    sanitized_output: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "is_protected": self.is_protected,
            "has_conflicts": self.has_conflicts,
            "conflict_logs": [c.to_dict() for c in self.conflict_logs],
            "sanitized_output": self.sanitized_output,
        }


class DeterministicValueProtector:
    """
    Validates AI-generated structured or text responses against authoritative deterministic engine values.
    Overwrites any conflicting AI figures with system-of-record values.
    """

    def sanitize_and_protect(
        self,
        ai_output: Dict[str, Any],
        context: ControlledInvestigationContext,
    ) -> ValueProtectionResult:
        case_id = context.case_id
        conflict_logs: List[ValueConflictLog] = []
        sanitized = dict(ai_output)

        # 1. Protect Financial Exposure Amounts
        deterministic_exposures = {e.get("exposure_id"): e for e in context.financial_exposures if e.get("exposure_id")}

        if "financial_impact" in sanitized and isinstance(sanitized["financial_impact"], list):
            sanitized_financial = []
            for item in sanitized["financial_impact"]:
                if isinstance(item, dict):
                    exp_id = item.get("exposure_id")
                    if exp_id and exp_id in deterministic_exposures:
                        det_exp = deterministic_exposures[exp_id]
                        det_amt = det_exp.get("amount")
                        ai_amt = item.get("amount")

                        if ai_amt is not None and det_amt is not None and abs(float(ai_amt) - float(det_amt)) > 0.01:
                            conflict_logs.append(
                                ValueConflictLog(
                                    field_name=f"financial_impact.{exp_id}.amount",
                                    ai_value=ai_amt,
                                    deterministic_value=det_amt,
                                    resolution=f"Overrode AI value {ai_amt} with authoritative engine value {det_amt}.",
                                )
                            )
                            item["amount"] = float(det_amt)

                        det_type = det_exp.get("exposure_type")
                        ai_type = item.get("exposure_type")
                        if ai_type and det_type and ai_type != det_type:
                            conflict_logs.append(
                                ValueConflictLog(
                                    field_name=f"financial_impact.{exp_id}.exposure_type",
                                    ai_value=ai_type,
                                    deterministic_value=det_type,
                                    resolution=f"Overrode AI type '{ai_type}' with deterministic type '{det_type}'.",
                                )
                            )
                            item["exposure_type"] = det_type
                    sanitized_financial.append(item)
            sanitized["financial_impact"] = sanitized_financial

        # 2. Protect Finding Statutory Verdicts and Observed Values
        deterministic_findings = {f.get("finding_id"): f for f in context.findings if f.get("finding_id")}

        if "what_was_detected" in sanitized and isinstance(sanitized["what_was_detected"], dict):
            det_sec = sanitized["what_was_detected"]
            f_ids = det_sec.get("finding_ids", [])
            for fid in f_ids:
                if fid in deterministic_findings:
                    det_f = deterministic_findings[fid]
                    # Ensure status/verdict is not modified by AI
                    if "verdict" in det_sec and det_sec["verdict"] != det_f.get("status"):
                        conflict_logs.append(
                            ValueConflictLog(
                                field_name=f"what_was_detected.{fid}.verdict",
                                ai_value=det_sec.get("verdict"),
                                deterministic_value=det_f.get("status"),
                                resolution="Preserved statutory gate status.",
                            )
                        )
                        det_sec["verdict"] = det_f.get("status")

        has_conflicts = len(conflict_logs) > 0
        return ValueProtectionResult(
            case_id=case_id,
            is_protected=True,
            has_conflicts=has_conflicts,
            conflict_logs=conflict_logs,
            sanitized_output=sanitized,
        )
