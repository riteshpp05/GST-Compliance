# UC15 — Intelligent Investigation Workspace & Audit Dossier Architecture
## Technical Reference Guide (Sprint 12.4)

---

### Executive Summary

Sprint 12.4 upgrades UC15 from a single-query agent into a **Persistent Intelligent Investigation Workspace**, enabling tax consultants and auditors to:
1. Conduct multi-turn investigation conversations with context retention.
2. Resolve implicit entity references (e.g. *"why is it non-compliant?"*, *"its financial exposure"*) against active entity focus (`EntityFocus`).
3. Accumulate deterministic findings and regulatory GST knowledge evidence across conversation turns.
4. Generate evidence-backed **Audit Dossiers** in JSON, GitHub-flavored Markdown, and downloadable **PDF** formats (`reportlab`).
5. Maintain strict read-only tool boundaries (`read_only=True`), input hardening against prompt injections, and explicit `INSUFFICIENT EVIDENCE / NOT AVAILABLE` notices.

---

### Target System Architecture

```
USER / UI WORKSPACE
         ↓
REST API (/api/agent/session/*)
         ↓
SESSION MANAGER (SessionManager & InMemorySessionRepository)
         ↓
AI INVESTIGATION AGENT (AIInvestigationAgent)
         ↓
GUARDRAILS & QUERY SANITIZER (sanitize_query & validate_plan)
         ↓
BOUNDED AGENTIC INVESTIGATION LOOP (InvestigationLoopEngine)
         ↓
DETERMINISTIC TOOLS (1-9) + GST KNOWLEDGE RAG TOOL (10)
         ↓
ACCUMULATED SESSION EVIDENCE & ENTITY FOCUS (EntityFocus)
         ↓
DOSSIER BUILDER & PDF EXPORTER (DossierBuilder & DossierPDFExporter)
         ↓
JSON / MARKDOWN / DOWNLOADABLE PDF AUDIT DOSSIER
```

---

### Key Components

#### 1. Multi-Turn Session Subsystem (`app/agent/ai/session.py`)
- **`EntityFocus`**: Tracks active entity scope (`invoice_id`, `counterparty_gstin`, `hsn_code`, `rule_category`, `risk_level`).
- **`InvestigationTurn`**: Captures raw query, resolved query, detected intent, executed tools, deterministic findings, regulatory evidence, and synthesized narrative.
- **`InvestigationSession`**: Domain model storing turns, accumulated evidence, contradictions, and focus.
- **`BaseSessionRepository` & `InMemorySessionRepository`**: Abstract repository pattern ensuring clean abstraction for future S14 PostgreSQL persistence.
- **`SessionManager`**: Handles context resolution, implicit pronoun matching, turn recording, and session lifecycle.

#### 2. Audit Dossier Engine (`app/agent/ai/dossier.py`)
- **`InvestigationDossier`**: Structured domain model containing:
  - Section 1: Executive Summary & Audit Verdict
  - Section 2: Multi-Turn Conversation Session Trail
  - Section 3: Statutory Compliance Gate Breakdown (Gates 1-6)
  - Section 4: Risk Profile & Financial Exposure Analysis
  - Section 5: Root Cause & Blast Radius Intelligence
  - Section 6: Regulatory Grounding & Statutory Provenance
  - Section 7: Advisory Resolution Actions & SAP Guidance
  - Section 8: Appendices & Audit Execution Trace
- **`DossierBuilder`**: Extracts and deduplicates accumulated evidence across session turns. Inserts explicit `INSUFFICIENT EVIDENCE / NOT AVAILABLE` notices for missing dimensions.

#### 3. PDF Exporter (`app/agent/ai/pdf_exporter.py`)
- **`DossierPDFExporter`**: Uses `reportlab.platypus` (SimpleDocTemplate, Paragraph, Table, HRFlowable) to build multi-page PDF audit reports with headers, color-coded status badges, data grids, and statutory provenance citations.

---

### REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/agent/session/start` | Initialize a new multi-turn investigation session. |
| `GET` | `/api/agent/sessions` | List active investigation workspace sessions. |
| `GET` | `/api/agent/session/{session_id}` | Retrieve session state, turn history, and entity focus. |
| `POST` | `/api/agent/session/{session_id}/query` | Submit multi-turn query to active session. |
| `POST` | `/api/agent/session/{session_id}/dossier` | Generate audit dossier (JSON & Markdown). |
| `GET` | `/api/agent/session/{session_id}/dossier/pdf` | Download formatted PDF audit report file. |

---

### Non-Negotiable Operational Rules Enforced

1. **In-Memory Session Abstraction**: Operates via `InMemorySessionRepository` behind `BaseSessionRepository` interface.
2. **Advisory SAP Guidance Only**: Action recommendations are strictly advisory (e.g. "Hold invoice from GSTR filing cycle"). Zero live SAP API calls or mutations.
3. **Evidence Provenance**: All major conclusions cite originating deterministic gate findings or regulatory document metadata.
4. **No Evidence Fabrication**: Any dimension without evidence is explicitly marked `INSUFFICIENT EVIDENCE / NOT AVAILABLE`.
5. **Read-Only Boundary**: All 10 tools enforce `read_only=True`.
