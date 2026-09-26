# UC15 GST Compliance Agent — AI Failure Handling & Provider Resilience

## Overview

In UC15, AI is **not a hard dependency** for compliance screening. If an LLM provider times out, fails, returns malformed JSON, or lacks an API key, the system degrades safely to deterministic synthesis mode without affecting compliance gate results or financial exposure totals.

---

## Handled Failure Scenarios

1. **Provider Timeout / Network Error:** Degrades cleanly to `LLMSynthesizer.create_deterministic_fallback`.
2. **Missing API Key (`DisabledProvider`):** Transparently operates in `DETERMINISTIC_FALLBACK` mode.
3. **Malformed JSON Output:** Sanitized by schema default parsers and converted into structured 6-part output.
4. **Production Mode (`APP_ENV=production`) Mock Attempt:** Requests for `MockProvider` in production environment trigger a security error log and return `DisabledProvider`, preventing silent mock fallback in production.

---

## Provider Status Modes

- **`REAL`:** Active LLM Provider (OpenAI, Vertex AI) with valid API credentials.
- **`MOCK`:** Controlled MockProvider for offline unit testing.
- **`DISABLED` / `DETERMINISTIC_FALLBACK`:** AI offline; deterministic compliance engines operational.
