# UC15 GST Compliance Agent — Evidence Grounding & Claim Validation Model

## Grounding Model

Every factual assertion produced by the AI assistant is evaluated by `EvidenceGroundingEvaluator` (`app/investigation/ai/grounding.py`).

---

## Grounding Status Taxonomy

- **`GROUNDED`:** Claim cites valid source IDs matching context facts with 100% precision.
- **`PARTIALLY_GROUNDED`:** Some cited source IDs exist in context, but secondary unknown citations exist.
- **`UNSUPPORTED`:** Claim cites zero valid source IDs or cites unknown source IDs.
- **`CONTRADICTED`:** Claim references contradictory evidence context signals.

---

## Dual Confidence Model

System Confidence and AI Confidence are **never** combined into a single ambiguous number:

- **System Confidence (`system_confidence`):** Deterministic statutory rule certainty based on gate results and evidence completeness.
- **AI Confidence (`ai_confidence`):** Explanation synthesis quality based on evidence grounding accuracy.
