# UC15 GST Compliance Agent — Empirical AI Evaluation & Measured Metrics

## Overview

Sprint 23 provides an empirical evaluation framework (`app/investigation/ai/metrics_evaluator.py`) tested against 15 synthetic AI evaluation scenarios (`tests/fixtures/synthetic_ai_eval_dataset.py`).

---

## Measured Evaluation Metrics

1. **Grounding Rate (`grounding_rate`):** Ratio of grounded factual claims to total claims.
2. **Unsupported Claim Rate (`unsupported_claim_rate`):** Ratio of unsupported claims detected and flagged.
3. **Citation Accuracy (`citation_accuracy`):** Precision of cited source IDs matching context source IDs.
4. **Financial Preservation Rate (`financial_preservation_rate`):** Ratio of runs where deterministic financial values were 100% preserved.
5. **Schema Validity Rate (`schema_validity_rate`):** Ratio of outputs conforming strictly to 6-part JSON schema.
6. **Hallucination Rejection Rate (`hallucination_rejection_rate`):** Ratio of detected hallucinations rejected by output guardrails.
7. **Provider Failure Recovery Rate (`provider_failure_recovery_rate`):** Ratio of clean fallbacks when LLM provider is offline.

---

## Evaluation Dataset Coverage

15 synthetic evaluation scenarios covering grounded findings, missing evidence, conflicting evidence, wrong financial amounts, unknown evidence IDs, unsupported GST rates, legal claim attempts, fraud claim attempts, clean invoices, multiple findings, multiple contradictions, provider failures, malformed responses, mock provider, and historical reference versions.
