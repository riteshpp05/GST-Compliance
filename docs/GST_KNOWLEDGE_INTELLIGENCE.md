# UC15 — Regulatory & GST Knowledge Intelligence Subsystem (Sprint 12.3)

## Executive Architecture Summary

Sprint 12.3 introduces the **Regulatory & GST Knowledge Intelligence** layer to the UC15 GST Compliance Platform.

This layer adds an evidence-grounded Retrieval-Augmented Generation (RAG) capability that integrates seamlessly with the existing Sprint 12.2 Bounded Agentic Investigation Loop.

```
USER QUERY
    ↓
INTENT (e.g. INVOICE_INVESTIGATION or REGULATORY_KNOWLEDGE)
    ↓
INITIAL PLAN
    ↓
DETERMINISTIC TOOLS (Gates 1-6, Risk Score, Financial Exposure)
    ↓
EVIDENCE
    ↓
EVIDENCE EVALUATION (Sufficiency & Discrepancy Checks)
    ↓
NEED REGULATORY KNOWLEDGE? (Yes)
    ↓
GST KNOWLEDGE RETRIEVAL (retrieve_gst_knowledge)
    ↓
REGULATORY EVIDENCE (Provenance, Temporal Applicability, Status)
    ↓
FINAL SYNTHESIS (Statutory Determination + Policy Explanation)
    ↓
AUDIT TRACE TIMELINE
```

---

## Non-Negotiable Core Architectural Boundary

> **IMPORTANT**: The deterministic GST engine remains the sole statutory authority for:
> - GST calculations & tax rates
> - GSTIN & HSN validations
> - Place of Supply & E-Way Bill validations
> - ITC eligibility verdicts & gate statuses
> - Financial exposure numbers & risk scores
>
> RAG/Knowledge Retrieval MUST NOT recalculate tax math, override compliance verdicts, or invent legal provisions. RAG exists strictly to provide supporting regulatory explanations, statutory circulars, policy context, and provenance.

---

## Knowledge Domain Architecture

The knowledge domain is implemented in the `app/knowledge/` package:

```
app/knowledge/
    __init__.py          # Package re-exports
    config.py            # KnowledgeConfig settings
    exceptions.py        # KnowledgeError, DocumentParsingError, DocumentSecurityError
    models.py            # Pydantic domain models & enums
    parsers/             # Secure DocumentParser implementations (PDF, DOCX, TXT, MD)
    chunking/            # DeterministicChunker pipeline
    embeddings/          # EmbeddingProvider abstraction (Mock & OpenAI)
    repository/          # KnowledgeRepository vector store abstraction (InMemory)
    retrieval/           # KnowledgeRetrievalService & contradiction engine
    service.py           # KnowledgeService main facade
```

---

## Knowledge Document Taxonomy

| DocumentType | Authority Level | Description |
| :--- | :---: | :--- |
| `GST_RULE` | 10 | Statutory CGST/SGST/IGST Act sections and rules |
| `GST_NOTIFICATION` | 8 | Official CBIC tax notifications |
| `GST_CIRCULAR` | 6 | CBIC departmental clarification circulars |
| `GST_FAQ` | 4 | Official GST portal FAQs |
| `COMPANY_POLICY` | 3 | Internal enterprise tax & procurement policy |
| `INTERNAL_CONTROL` | 2 | Internal audit & control guidelines |

---

## Document Ingestion & Security Controls

Supported formats: `.pdf`, `.docx`, `.txt`, `.md`, `.markdown`.

### Security Protections
1. **Path Traversal Protection**: Rejects file paths containing `..` or null byte `\0` characters.
2. **Extension Allow-List**: Prohibits unapproved file extensions (e.g. `.exe`, `.py`, `.sh`).
3. **File Size Enforcement**: Bounded by `max_file_size_bytes` (default 10 MB).
4. **Data-Only Execution**: Uploaded documents are treated strictly as static text data. No code execution permitted.

---

## Deterministic Chunking Pipeline

Implemented in `app/knowledge/chunking/pipeline.py`:
- **Regulatory Structure Respect**: Respects page markers (`--- [Page N] ---`) and section headings (`Section X`, `Rule Y`, `Clause Z`).
- **Sliding Character Window**: Enforces `chunk_size` (default 500 chars) and `chunk_overlap` (default 50 chars).
- **Deterministic Chunk IDs**: Generates SHA-256 hash seeds from `doc_id`, page, section, and index: `CHK-{doc_id}-{hash}`.
- **Content Deduplication**: Skips duplicate identical content blocks.

---

## Embedding & Vector Store Abstraction

- **`EmbeddingProvider`**: Abstract interface (`embed_text`, `embed_batch`).
  - **`DeterministicMockEmbeddingProvider`**: Generates 128-dimensional L2-normalized vectors based on character n-grams and word tokens. 100% deterministic, zero external API dependency.
  - **`OpenAIEmbeddingProvider`**: Connects to OpenAI API (`text-embedding-3-small`) if `OPENAI_API_KEY` is present; falls back to mock provider if key is absent or API fails.
- **`KnowledgeRepository`**: Abstract vector store interface.
  - **`InMemoryKnowledgeRepository`**: Thread-safe in-memory index calculating cosine similarity. Decoupled from specific vector DBs, permitting future `pgvector` migration.

---

## Temporal & Effective-Date-Aware Retrieval

Implemented in `KnowledgeRetrievalService`:
- When `transaction_date` (YYYY-MM-DD) is provided:
  - Validates `effective_from` <= `transaction_date` <= `effective_to`.
  - If document was not yet active or has expired, marks `temporal_applicable = False` and status `EXPIRED`.
  - Ranks temporal-applicable knowledge higher than expired knowledge.

---

## Evidence Quality & Contradiction Detection

### Evidence Quality Statuses
- `SUPPORTED`: Cosine relevance score >= 0.7.
- `PARTIALLY_SUPPORTED`: Cosine relevance score 0.4–0.7.
- `LOW_RELEVANCE`: Cosine relevance score 0.2–0.4.
- `NO_EVIDENCE`: Cosine relevance score < 0.2.
- `EXPIRED`: Failed temporal validity check.
- `CONFLICTING`: Contradictory evidence detected across retrieved sources.

### Contradiction Detection Engine
Detects cross-document contradictions (e.g. Document A specifies 18% tax rate while Document B specifies 12% tax rate for the same topic, or one document blocks ITC while another allows it). Returns `conflicts_detected = True` without fabricating resolutions.

---

## Read-Only Knowledge Tool (`retrieve_gst_knowledge`)

Registered in `ToolRegistry` with `read_only=True`:
- **Name**: `retrieve_gst_knowledge`
- **Category**: `KNOWLEDGE`
- **Allow-Listed Intents**: `INVOICE_INVESTIGATION`, `COUNTERPARTY_INVESTIGATION`, `RISK_ANALYSIS`, `ROOT_CAUSE_ANALYSIS`, `GENERAL_COMPLIANCE`, `REGULATORY_KNOWLEDGE`.
- **Inputs**: `query`, `topic`, `transaction_date`, `jurisdiction`, `document_type`, `top_k`.

---

## REST API & Web UI Extensions

- **`POST /api/agent/investigate`**: Returns `knowledge_evidence` array with document name, source, page, section, relevance, effective dates, and evidence status.
- **Read-Only Endpoints**:
  - `GET /api/knowledge/status`
  - `GET /api/knowledge/documents`
  - `POST /api/knowledge/retrieve`
  - `POST /api/knowledge/upload` (Secured with extension/size/path checks).
- **Web UI (`#/ai_agent`)**:
  - **Retrieved Regulatory GST Evidence Card**: Renders document name, source, page, section, relevance badge, and evidence status badge.
  - **Trace Timeline Distinction**: Visually distinguishes `DETERMINISTIC ENGINE TOOL` from `REGULATORY KNOWLEDGE RAG`.
  - **Warning Cards**: Highlights `CONFLICTING`, `LOW_RELEVANCE`, `EXPIRED`, or `NO_EVIDENCE` status.
