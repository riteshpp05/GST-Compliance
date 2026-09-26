# Case Management & Human Approval Subsystem (Sprint 13)

## 1. Executive Summary & Objective
Sprint 13 introduces an operational **Case Management and Human Approval Layer** on top of UC15's deterministic statutory engines (S1–S11) and controlled AI investigation agent architecture (S12.1–S12.4).

### Fundamental Business Principle
> **AI investigates. AI explains. AI recommends. Human reviews. Human decides.**

The AI agent conducts evidence-first investigations, performs RAG knowledge retrieval, synthesizes findings, and formats advisory ERP guidance. However, the AI agent is **strictly prohibited** from approving cases, rejecting cases, mutating SAP/ERP systems, executing financial entries, or bypassing human authorization.

---

## 2. Architecture & System Flow

```
USER / CONSULTANT
       │
       ▼
INVESTIGATION WORKSPACE (S12.4)
       │
       ▼
INVESTIGATION SESSION (S12.4)
       │
       ▼
BOUNDED AI AGENT (S12.1-S12.3)
       │
       ▼
DETERMINISTIC COMPLIANCE & GST KNOWLEDGE (S1-S12.3)
       │
       ▼
EVIDENCE ACCUMULATION & PROVENANCE
       │
       ▼
INVESTIGATION DOSSIER (S12.4)
       │
       ▼
CASE MANAGEMENT SUBSYSTEM (S13)
       │
       ▼
HUMAN REVIEW & DECISION AUTHORIZATION
       │
 ┌─────┴───────────────────────────────┐
 │ APPROVE                             │
 │   ↓                                 │
 │ READY_FOR_RESOLUTION (S13 Boundary) │
 │                                     │
 │ REJECT                              │
 │   ↓                                 │
 │ REJECTED                            │
 │                                     │
 │ REQUEST_MORE_EVIDENCE               │
 │   ↓                                 │
 │ INVESTIGATING (S12.4 AI Re-run)     │
 │   ↓                                 │
 │ REVIEW_REQUIRED                     │
 └─────────────────────────────────────┘
```

---

## 3. Case Domain Models (`app/case/models.py`)

- **`InvestigationCase`**: Domain model representing an operational investigation case. Contains `case_id` (`CASE-XXXXXXXX`), `title`, `description`, `status`, `priority`, `risk_level`, `source_session_id`, `source_dossier_id`, `invoice_id`, `counterparty_gstin`, `counterparty_name`, `assigned_to`, `assigned_role`, `financial_exposure`, `root_cause`, `blast_radius`, `recommendation`, `evidence_references`, and `decisions`.
- **`CaseDecision`**: Structured record of human review containing `decision_id`, `case_id`, `reviewer`, `reviewer_role`, `decision` (`APPROVE`, `REJECT`, `REQUEST_MORE_EVIDENCE`), `comment`, `requested_evidence`, and `timestamp`.
- **`CaseEvent`**: Append-only audit timeline entry tracking `event_id`, `case_id`, `event_type`, `actor`, `timestamp`, `previous_status`, `new_status`, and `metadata`.
- **`CaseEvidenceReference`**: Explicit evidence link preserving provenance (`source_type`, `source_identifier`, `invoice_id`, `gate_id`, `dossier_id`, `session_id`, `document_id`, `section`, `relevance_score`).

---

## 4. Case State Machine Lifecycle (`app/case/state_machine.py`)

```
                 ┌──────────────┐
                 │     OPEN     │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │INVESTIGATING │◄─────────────────┐
                 └──────┬───────┘                  │
                        │                          │
                        ▼                          │
                 ┌──────────────┐                  │
                 │REVIEW_REQUIRED│                  │
                 └──────┬───────┘                  │
                        │                          │
     ┌──────────────────┼──────────────────┐       │
     │ (Human Decision) │ (Human Decision) │       │
     ▼                  ▼                  ▼       │
┌──────────┐      ┌──────────┐  ┌──────────────────────┐
│ APPROVED │      │ REJECTED │  │MORE_EVIDENCE_REQUIRED│
└────┬─────┘      └──────────┘  └──────────┬───────────┘
     │                                     │
     ▼                                     └───────┘
┌──────────────────────┐
│ READY_FOR_RESOLUTION │
└──────────────────────┘
```

### State Machine Transition Rules & Enforcements:
1. Moving from `REVIEW_REQUIRED` to `APPROVED`, `REJECTED`, or `MORE_EVIDENCE_REQUIRED` requires an explicit human review submission with a valid `reviewer` identity and non-empty comment.
2. An `APPROVED` case automatically follows through to `READY_FOR_RESOLUTION`.
3. Any attempt by an AI actor to approve, reject, or transition a case to `READY_FOR_RESOLUTION` raises `CaseStateTransitionError`.
4. Invalid jumps (e.g. `OPEN` → `APPROVED` or `INVESTIGATING` → `APPROVED`) raise `CaseStateTransitionError`.

---

## 5. Repository Abstraction (`app/case/repository.py`)

- **`BaseCaseRepository`**: Abstract base class defining CRUD methods for cases, events, decisions, and evidence references.
- **`InMemoryCaseRepository`**: Thread-safe in-memory repository implementation used for Sprint 13.
- **Storage Boundary Notice**: S13 case storage is in-memory and does not persist across process restarts. Full durable PostgreSQL persistence will be introduced in **Sprint 14**.

---

## 6. Controlled More-Evidence Workflow

When a human reviewer selects `REQUEST_MORE_EVIDENCE`:
1. `CaseService.request_more_evidence_workflow()` records the human decision and transitions the case to `MORE_EVIDENCE_REQUIRED`.
2. The case status transitions to `INVESTIGATING`.
3. The service delegates to `AIInvestigationAgent` on the `source_session_id` using the exact S12.4 bounded architecture (tool allow-list, investigation budget, guardrails, RAG service).
4. Newly retrieved regulatory evidence or findings are accumulated as new `CaseEvidenceReference` items on the case.
5. The updated dossier refreshes the case summary and advisory recommendation.
6. The case status transitions back to `REVIEW_REQUIRED` for human review re-evaluation.

---

## 7. Security Boundaries & Architectural Controls

1. **AI Boundary**: AI agent acts solely as an investigator, evidence retriever, and recommender. AI **cannot** perform approval or rejection.
2. **SAP / ERP Boundary**: SAP recommendations retain mandatory `[ADVISORY SAP / FINANCE ACTION]` header. No live RFC, BAPI, OData, CDS, or SAP database mutations occur.
3. **Resolution Boundary**: S13 ends at status `READY_FOR_RESOLUTION`. No automated financial resolution or revalidation execution is performed (deferred to **Sprint 18**).
4. **Auth / RBAC Boundary**: Mock/controlled reviewer identities are passed explicitly. Enterprise auth, SSO, and multi-tenancy are deferred to **Sprint 19**.
5. **MCP / ML Boundary**: No MCP or ML models are used (deferred to **Sprint 20**).

---

## 8. REST API Endpoints (`ui/app.py`)

- `POST /api/cases` — Create an InvestigationCase from `session_id` or `dossier_id`.
- `GET /api/cases` — List cases with optional `status`, `priority`, or `invoice_id` filters.
- `GET /api/cases/{case_id}` — Retrieve detailed case model.
- `POST /api/cases/{case_id}/assign` — Assign or reassign case to a reviewer/analyst.
- `POST /api/cases/{case_id}/review` — Submit human review decision (`APPROVE`, `REJECT`, `REQUEST_MORE_EVIDENCE`).
- `GET /api/cases/{case_id}/timeline` — Retrieve chronological case audit event history.
- `GET /api/cases/{case_id}/evidence` — Retrieve linked case evidence references.

---

## 9. Downstream Sprint Dependencies & Roadmap

- **Sprint 14**: Introduction of PostgreSQL persistence for durable `CaseRepository` storage.
- **Sprint 16**: Real read-only SAP integration (CDS / OData).
- **Sprint 18**: Controlled automated resolution execution and post-resolution statutory revalidation.
- **Sprint 19**: Enterprise Authentication, Role-Based Access Control (RBAC), and Multi-Tenancy.
- **Sprint 20**: Advanced MCP and ML predictive intelligence integration.
