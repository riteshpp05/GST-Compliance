"""
app.investigation.ai package
=============================
Hardened AI investigation assistance layer for UC15 (Sprint 23).
Provides context building, evidence grounding, deterministic value protection,
anti-hallucination output validation, hardened prompts, dual confidence semantics,
audit logging, and measured evaluation metrics.
"""
from app.investigation.ai.context_builder import CanonicalAIContextBuilder, ControlledInvestigationContext
from app.investigation.ai.grounding import EvidenceGroundingEvaluator, AIClaim, GroundingStatus
from app.investigation.ai.value_protector import DeterministicValueProtector, ValueProtectionResult
from app.investigation.ai.output_validator import AIOutputValidator, OutputValidationResult
from app.investigation.ai.prompts import HardenedPromptManager, PROMPT_VERSION, CONTEXT_SCHEMA_VERSION
from app.investigation.ai.confidence import DualConfidenceModel, DualConfidenceResult
from app.investigation.ai.audit_logger import AIAuditLogger
from app.investigation.ai.metrics_evaluator import AIMetricsEvaluator

__all__ = [
    "CanonicalAIContextBuilder",
    "ControlledInvestigationContext",
    "EvidenceGroundingEvaluator",
    "AIClaim",
    "GroundingStatus",
    "DeterministicValueProtector",
    "ValueProtectionResult",
    "AIOutputValidator",
    "OutputValidationResult",
    "HardenedPromptManager",
    "PROMPT_VERSION",
    "CONTEXT_SCHEMA_VERSION",
    "DualConfidenceModel",
    "DualConfidenceResult",
    "AIAuditLogger",
    "AIMetricsEvaluator",
]
