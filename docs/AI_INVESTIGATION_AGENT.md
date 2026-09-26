# UC15 — Controlled AI Investigation Agent Foundation & Bounded Loop (Sprint 12.1 & 12.2)

## Executive Architecture Summary

Sprint 12.1 & 12.2 introduce the **Controlled AI Investigation Agent** with a **Bounded Agentic Loop** to the UC15 GST Compliance Platform.

Unlike unconstrained chatbots or unguided autonomous agents, the UC15 AI Agent operates under strict **evidence-first control principles**:
1. **Deterministic Authority**: All statutory compliance outcomes, tax rate validations, risk scores, duplicate matches, and financial exposure numbers are calculated strictly by the deterministic S1–S11 engines.
2. **LLM as Synthesizer & Guided Selector, Not Calculator**: The LLM NEVER recalculates financial math, invents statutory rules, or asserts unverified facts. Its sole role is reasoning over evidence payloads and selecting the next allowed tool from intent-governed allow-lists.
3. **Read-Only Enforcement**: All registered tools wrapping S1–S11 engines are strictly `read_only=True`. The tool registry raises hard runtime `ValueError` exceptions if any mutating tool is attempted to be registered.
4. **Bounded Agentic Loop**: Upgraded from single-step execution to a bounded iterative loop (`USER QUERY -> INTENT -> INITIAL PLAN -> TOOL -> EVIDENCE -> EVALUATION -> NEED MORE EVIDENCE? -> NEXT TOOL -> SYNTHESIS`).
5. **Configurable Execution Budget**: Loop iterations are bounded by explicit limits (`max_steps=5`, `max_tool_calls=7`, `max_execution_time_seconds=20.0`). Exceeding budget gracefully terminates with `BUDGET_EXHAUSTED`.
6. **Trace Transparency**: Every loop iteration records a structured `TraceStep` capturing action type, tool arguments, status, execution timing, and result summary for full auditability.
7. **Contradiction Detection**: `EvidenceEvaluator` checks cross-tool evidence for contradictions (e.g. `COMPLIANT` verdict vs `HIGH` risk level) and highlights them in the response and UI.
8. **Graceful Fallback**: When no LLM API key is present in the environment (`LLM_API_KEY` / `OPENAI_API_KEY`), the system seamlessly falls back to deterministic tool selection and structured synthesis without crashing or fabricating fake AI output.

---

## 7-Stage Controlled Investigation Pipeline & Loop Architecture

```
[USER QUERY]
     │
     ▼
┌────────────────────────────────────────┐
│ 1. Deterministic Intent Detection      │  (Keyword/Pattern matching across 10 controlled intents)
└────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│ 2. Investigation Planner               │  (Maps intent to approved read-only tool subset)
└────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐
│ 3. Agent Safety Guardrails Audit       │  (Verifies all plan tools are registered & read-only)
└────────────────────────────────────────┘
     │
     ▼
┌────────────────────────────────────────┐ ◄─── ITERATIVE LOOP ENGINE ───┐
│ 4. Investigation Loop Engine           │                             │
│    - Initialize InvestigationState     │                             │
│    - Check Budget Limits & Timeout     │                             │
│    - EvidenceEvaluator Sufficiency     │ ───────[NEED MORE EVIDENCE]───┤
│    - ControlledToolSelector Next Tool  │                             │
│    - Read-Only Tool Execution          │                             │
│    - Record Audit TraceStep            │                             │
└────────────────────────────────────────┘                             │
     │ [EVIDENCE SUFFICIENT / BUDGET EXHAUSTED / NO MORE TOOLS]        │
     ▼                                                                 │
┌────────────────────────────────────────┐                             │
│ 5. Evidence Context Builder Assembly   │                             │
└────────────────────────────────────────┘                             │
     │                                                                 │
     ▼                                                                 │
┌────────────────────────────────────────┐                             │
│ 6. Provider Synthesis / Fallback       │                             │
└────────────────────────────────────────┘                             │
     │                                                                 │
     ▼                                                                 │
┌────────────────────────────────────────┐                             │
│ 7. Schema Validation & Guardrails      │                             │
└────────────────────────────────────────┘                             │
     │                                                                 │
     ▼                                                                 │
[INVESTIGATION RESPONSE + AUDIT TRACE TIMELINE] ───────────────────────┘
```

---

## Bounded Execution Budget & Safety Limits

- **`max_steps`**: Bounded iteration steps (default: 5, range: 1–20).
- **`max_tool_calls`**: Maximum total tool calls across investigation (default: 7, range: 1–30).
- **`max_execution_time_seconds`**: Hard execution timeout (default: 20.0s, range: 0.001–120.0s).
- **Termination Criteria**:
  - `SUFFICIENT_EVIDENCE`: Evaluator deems evidence complete.
  - `NO_MORE_ALLOWED_TOOLS`: All intent-approved tools executed.
  - `MAX_STEPS_REACHED`: Iteration limit hit.
  - `MAX_TOOL_CALLS_REACHED`: Tool call limit hit.
  - `TIMEOUT`: Execution time threshold exceeded.

---

## Controlled Intent Taxonomy

| Intent Enum | Description | Approved Read-Only Tools |
| :--- | :--- | :--- |
| `INVOICE_INVESTIGATION` | Deep-dive risk & compliance audit for a specific invoice | `get_compliance_result`, `get_risk_assessment`, `validate_invoice`, `get_financial_exposure` |
| `COUNTERPARTY_INVESTIGATION` | Vendor compliance risk & exposure analysis | `get_risk_assessment`, `get_compliance_result`, `get_financial_exposure`, `get_blast_radius` |
| `RISK_ANALYSIS` | Risk score & category profile investigation | `get_risk_assessment`, `get_compliance_result` |
| `FINANCIAL_EXPOSURE` | Total financial exposure & ineligible ITC risk | `get_financial_exposure`, `get_risk_assessment` |
| `HISTORICAL_ANALYSIS` | Historical compliance trends across filing periods | `get_historical_patterns`, `get_compliance_result` |
| `DUPLICATE_ANALYSIS` | Near-duplicate invoice pair detection | `find_duplicates`, `get_risk_assessment` |
| `ANOMALY_ANALYSIS` | Statistical value & tax rate anomaly investigation | `find_anomalies`, `get_risk_assessment` |
| `ROOT_CAUSE_ANALYSIS` | Dominant failure root-cause pattern analysis | `investigate_root_cause`, `get_historical_patterns`, `get_compliance_result` |
| `BLAST_RADIUS_ANALYSIS` | Ecosystem impact & blast radius for vendor/HSN | `get_blast_radius`, `get_financial_exposure` |
| `GENERAL_COMPLIANCE` | General compliance inquiry fallback | `get_compliance_result`, `get_risk_assessment`, `get_financial_exposure` |

---

## Read-Only Tool Registry

All 9 tools wrap existing, proven S1–S11 deterministic engines:

1. `validate_invoice`: Executes Gates 1–6 statutory compliance rules on an invoice.
2. `get_compliance_result`: Fetches statutory validation results and failed gate details.
3. `get_risk_assessment`: Retrieves 0–100 risk scores, risk levels (LOW..CRITICAL), and categories.
4. `get_financial_exposure`: Aggregates tax exposure, ITC ineligible amount, and penalty risk.
5. `get_historical_patterns`: Analyzes compliance performance across historical periods.
6. `find_duplicates`: Runs duplicate detection algorithms to find duplicate pairs/groups.
7. `find_anomalies`: Runs statistical anomaly detection across taxable values and tax rates.
8. `investigate_root_cause`: Extracts primary root causes (e.g. Master Data mismatch, POS error).
9. `get_blast_radius`: Computes vendor/HSN/GSTIN blast radius and downstream impact score.

---

## Provider Architecture & Zero API Key Hardcoding

The AI Provider abstraction supports three operating modes:

- **`DisabledProvider` (Default when no API key present)**: Returns structured deterministic evidence synthesis. Zero API calls made. Zero test failures.
- **`MockProvider`**: Used during isolated testing to verify LLM prompt generation without incurring API charges.
- **`OpenAIProvider`**: Connects to OpenAI API (or compatible endpoint) using structured JSON output formatting. Enabled via `OPENAI_API_KEY` environment variable.

```python
# Provider initialization logic
from app.agent.ai.provider import create_llm_provider, LLMConfig

config = LLMConfig.from_env() # Reads OPENAI_API_KEY from environment
provider = create_llm_provider(config)
```

---

## Safety Guardrails & Verification

1. **Read-Only Guardrail**: `AgentGuardrails.audit_plan()` verifies that every tool in an investigation plan exists in `ToolRegistry` and has `read_only=True`.
2. **Intent Allow-List Guardrail**: Tool selector rejects any tool not explicitly listed in `INTENT_TOOL_MAPPINGS`.
3. **Duplicate Tool Prevention**: Already executed tools in an investigation run are automatically skipped.
4. **Input Hardening**: Query strings are sanitized, truncated to 500 characters max, and checked for empty/whitespace input.
5. **Response Schema Validation**: The response object is validated against `InvestigationResponse` Pydantic model to guarantee proper field types.

---

## REST API Endpoint

### `POST /api/agent/investigate`

**Request Body:**
```json
{
  "query": "Why is invoice INV-8000001 high risk?",
  "invoice_id": "INV-8000001",
  "force_fallback": false
}
```

**Response Body:**
```json
{
  "query": "Why is invoice INV-8000001 high risk?",
  "intent": {
    "intent": "INVOICE_INVESTIGATION",
    "confidence": 1.0,
    "reasoning": "Extracted intent INVOICE_INVESTIGATION",
    "extracted_invoice_id": "INV-8000001"
  },
  "plan": {
    "intent": "INVOICE_INVESTIGATION",
    "tools_to_call": ["get_compliance_result", "get_risk_assessment"],
    "rationale": "Executed read-only tools for INVOICE_INVESTIGATION"
  },
  "tool_results": [ ... ],
  "synthesized_answer": "### DETERMINISTIC EVIDENCE SUMMARY ...",
  "provider_status": {
    "available": false,
    "provider_type": "disabled",
    "model": "none"
  },
  "guardrails_passed": true,
  "confidence_score": 0.95,
  "execution_time_ms": 15.0,
  "investigation_id": "INVEST-D0E31284",
  "investigation_status": "EVIDENCE_SUFFICIENT",
  "termination_reason": "SUFFICIENT_EVIDENCE",
  "investigation_steps": [
    {
      "step_number": 1,
      "action_type": "INTENT_AND_PLANNING",
      "tool_name": null,
      "arguments": {},
      "result_summary": "Classified intent 'INVOICE_INVESTIGATION'...",
      "status": "SUCCESS",
      "execution_time_ms": 5.0
    },
    {
      "step_number": 2,
      "action_type": "TOOL_EXECUTION",
      "tool_name": "get_compliance_result",
      "arguments": {"invoice_no": "INV-8000001"},
      "result_summary": "Tool 'get_compliance_result' executed cleanly in 12.5ms.",
      "status": "SUCCESS",
      "execution_time_ms": 12.5
    }
  ],
  "evidence_sufficiency": {
    "sufficient": true,
    "status": "EVIDENCE_SUFFICIENT"
  },
  "contradictions": []
}
```

---

## UI Component

The AI Agent view is available in the web UI under **AI Investigation Agent** tab (`#/ai_agent`).
It features:
- Interactive query input box with pre-populated sample queries.
- Header status bar with `investigation_id`, status badges, and termination criteria.
- Rendered markdown investigation synthesis with evidence badges.
- Visual **Investigation Audit Trace Timeline** showing step-by-step reasoning, tool execution timings, and arguments.
- **Evidence Contradictions Warning Card** highlighting conflicting evidence between tools.
- Expandable raw tool results drawer for complete auditability.

---

## Scope & Non-Goals

The Sprint 12.2 Controlled AI Investigation Agent explicitly does **NOT**:
- Modify invoice data, database records, or configuration files.
- Integrate with SAP, ERP, or external payment gateways.
- Perform vector database RAG indexing or external web searches.
- Override or recalculate statutory compliance gate results.
