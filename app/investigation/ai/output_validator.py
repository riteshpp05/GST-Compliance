"""
UC15 GST Compliance Agent — Anti-Hallucination AI Output Validator (Sprint 23)
Scans AI-generated responses for unknown IDs, unsupported legal/fraud claims,
unauthorized decision attempts, and hallucinated references.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.investigation.ai.context_builder import ControlledInvestigationContext
from app.investigation.ai.grounding import EvidenceGroundingEvaluator, GroundingStatus, AIClaim
from app.investigation.ai.value_protector import DeterministicValueProtector, ValueProtectionResult


@dataclass
class OutputValidationResult:
    case_id: str
    status: str = "VALID"  # VALID | PARTIALLY_VALID | REJECTED
    accepted_sections: List[str] = field(default_factory=list)
    rejected_claims: List[Dict[str, Any]] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    value_protection: Optional[ValueProtectionResult] = None
    sanitized_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "accepted_sections": self.accepted_sections,
            "rejected_claims": self.rejected_claims,
            "validation_errors": self.validation_errors,
            "value_protection": self.value_protection.to_dict() if self.value_protection else None,
            "sanitized_response": self.sanitized_response,
        }


class AIOutputValidator:
    """
    Validation engine scanning AI investigation outputs against strict safety guardrails.
    """

    FORBIDDEN_LEGAL_TERMS = [
        "guilty of fraud",
        "tax evasion confirmed",
        "fraudulent scheme",
        "court liability",
        "legal conviction",
        "criminal offense",
    ]

    FORBIDDEN_DECISION_TERMS = [
        "reject invoice",
        "approve case",
        "close case",
        "resolve case",
        "override rule",
    ]

    def __init__(
        self,
        value_protector: Optional[DeterministicValueProtector] = None,
        grounding_evaluator: Optional[EvidenceGroundingEvaluator] = None,
    ) -> None:
        self.value_protector = value_protector or DeterministicValueProtector()
        self.grounding_evaluator = grounding_evaluator or EvidenceGroundingEvaluator()

    def validate_output(
        self,
        ai_response_dict: Dict[str, Any],
        context: ControlledInvestigationContext,
    ) -> OutputValidationResult:
        case_id = context.case_id
        errors: List[str] = []
        rejected: List[Dict[str, Any]] = []
        accepted_sections: List[str] = []

        # 1. Deterministic Value Protection
        prot_res = self.value_protector.sanitize_and_protect(ai_response_dict, context)
        sanitized = prot_res.sanitized_output

        # 2. Check for Forbidden Legal / Fraud Claims in text fields
        full_text_corpus = " ".join([
            str(v) for k, v in sanitized.items()
            if isinstance(v, (str, list, dict))
        ])

        for term in self.FORBIDDEN_LEGAL_TERMS:
            if re.search(r"\b" + re.escape(term) + r"\b", full_text_corpus, flags=re.IGNORECASE):
                err = f"Guardrail violation: AI output contains forbidden legal/fraud assertion '{term}'."
                errors.append(err)
                rejected.append({
                    "type": "FORBIDDEN_LEGAL_ASSERTION",
                    "term": term,
                    "reason": "AI is forbidden from declaring legal liability or fraud convictions.",
                })

        # 3. Check for Unauthorized Human Decision Commands
        next_steps = sanitized.get("next_steps", [])
        clean_next_steps = []
        if isinstance(next_steps, list):
            for step in next_steps:
                step_str = str(step)
                has_cmd = False
                for cmd in self.FORBIDDEN_DECISION_TERMS:
                    if cmd.lower() in step_str.lower():
                        has_cmd = True
                        rejected.append({
                            "type": "UNAUTHORIZED_DECISION_COMMAND",
                            "command": cmd,
                            "step_text": step_str,
                            "reason": "AI is forbidden from executing or commanding human-only case decisions.",
                        })
                        break
                if not has_cmd:
                    clean_next_steps.append(step)
            sanitized["next_steps"] = clean_next_steps

        # 4. Unknown Source ID Validation
        valid_sources = context.get_valid_source_ids()

        def scan_ids(obj: Any):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ("finding_ids", "evidence_ids", "exposure_ids", "source_ids") and isinstance(v, list):
                        for sid in v:
                            if sid not in valid_sources:
                                errors.append(f"Guardrail violation: Unknown source ID '{sid}' cited in output.")
                                rejected.append({
                                    "type": "UNKNOWN_SOURCE_ID",
                                    "source_id": sid,
                                    "reason": "Source ID does not exist in investigation context.",
                                })
                    else:
                        scan_ids(v)
            elif isinstance(obj, list):
                for elem in obj:
                    scan_ids(elem)

        scan_ids(sanitized)

        # 5. Evaluate Accepted Sections
        standard_sections = [
            "what_was_detected",
            "supporting_evidence",
            "conflicts_and_contradictions",
            "financial_impact",
            "missing_evidence",
            "next_steps",
        ]
        for sec in standard_sections:
            if sec in sanitized and sanitized[sec]:
                accepted_sections.append(sec)

        # Determine overall status
        if rejected and len(rejected) > 3:
            status = "REJECTED"
        elif rejected or errors:
            status = "PARTIALLY_VALID"
        else:
            status = "VALID"

        return OutputValidationResult(
            case_id=case_id,
            status=status,
            accepted_sections=accepted_sections,
            rejected_claims=rejected,
            validation_errors=errors,
            value_protection=prot_res,
            sanitized_response=sanitized,
        )
