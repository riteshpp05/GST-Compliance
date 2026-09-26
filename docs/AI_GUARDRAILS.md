# UC15 GST Compliance Agent — AI Safety & Anti-Hallucination Guardrails

## Overview

The `AIOutputValidator` (`app/investigation/ai/output_validator.py`) and `AgentGuardrails` (`app/agent/ai/guardrails.py`) enforce non-negotiable safety guardrails on all AI-generated outputs.

---

## Enforced Guardrail Rules

1. **Unknown Source ID Rejection:** Every cited finding, evidence, exposure, or contradiction ID must exist in `ControlledInvestigationContext.get_valid_source_ids()`. Fabricated IDs are rejected.
2. **Forbidden Legal Claims:** AI is strictly forbidden from asserting legal guilt or fraud convictions ("guilty of fraud", "tax evasion confirmed"). Terms are redacted and flagged as `FORBIDDEN_LEGAL_ASSERTION`.
3. **Forbidden Decision Commands:** AI is forbidden from commanding human case transitions ("reject invoice", "approve case"). Commands are stripped and flagged as `UNAUTHORIZED_DECISION_COMMAND`.
4. **Deterministic Value Overrides:** Any monetary amount or tax rate differing from the deterministic context is replaced by `DeterministicValueProtector`.

---

## Validation Statuses

- **`VALID`:** Response satisfies 100% of guardrails and source ID grounding rules.
- **`PARTIALLY_VALID`:** Minor unknown ID citations or forbidden phrasing detected; sanitized automatically.
- **`REJECTED`:** Critical guardrail failures; fallback response returned.
