# UC15 Architecture Specification: Client-Ready Finance GST Compliance Agent

**Document Version:** 3.0.0  
**Status:** Productization Architecture Map  
**Core Principle:** Deterministic Statutory Engine (Layer A) + AI Explanation & Advisory Layer (Layer B)  

---

## 1. System Data & Control Flow

```mermaid
flowchart TD
    subgraph Layer 0: Finance Ingestion & Data Lineage
        DS1[SAP S/4HANA OData / CDS Views] --> CAN[Canonical Finance Transaction Model]
        DS2[Excel / CSV / JSON Ingestion] --> CAN
        DS3[GST Portal GSTR-2B / E-Invoice / EWB] --> CAN
    end

    subgraph Layer A: Deterministic Engine (Zero LLM, 100% Testable)
        CAN --> DQ[Data Quality Engine]
        DQ --> APP[Applicability Engine]
        APP --> DEP[Rule Dependency Graph]
        DEP --> SEC[Core Statutory Engine: Gates 1-6 + Extended]
        SEC --> DEC[Compliance Decision & Confidence Model]
        DEC --> FIN[Financial Impact Engine]
    end

    subgraph Layer B: Exception Management & AI Agent Layer
        FIN --> EXC[Exception Management Hub]
        EXC --> AI[Agentic AI Explanation & Inquiry Engine]
        EXC --> RES[Assisted Resolution & Approval Workflow]
        RES --> AUD[Immutable Audit Trail & Lineage Tracker]
    end
```

---

## 2. Component Mapping Matrix

| Layer / Stage | Subsystem / Component | Responsibilities & Architectural Contract |
| :--- | :--- | :--- |
| **Layer 0** | **Canonical Data Model** | Normalizes raw SAP/Excel fields into `CanonicalTransaction` with explicit data lineage (`source_system`, `source_field`, `retrieved_at`). |
| **Layer A1** | **Data Quality Engine** | Evaluates usability before compliance checks. Assigns `VALID`, `MISSING`, `INVALID`, `CONFLICTING`, `STALE`, or `UNAVAILABLE`. Prevents missing data from becoming false statutory failures. |
| **Layer A2** | **Applicability Engine** | Answers `APPLICABLE`, `NOT_APPLICABLE`, or `UNKNOWN` per transaction before rule execution (e.g. Sales AR $\rightarrow$ ITC Not Applicable; Services $\rightarrow$ E-Way Bill Not Applicable). |
| **Layer A3** | **Rule Dependency Graph** | Executes upstream dependencies (GSTIN $\rightarrow$ Classification $\rightarrow$ POS $\rightarrow$ Tax $\rightarrow$ EWB/E-Invoice $\rightarrow$ ITC/RCM). Prevents invalid upstream data from triggering downstream false failures. |
| **Layer A4** | **Core Statutory Engine** | Validates GSTIN, HSN/SAC, Tax Rates, POS, E-Invoice, E-Way Bill, ITC, RCM, Credit Notes, 180-day payments against CBIC notifications. |
| **Layer A5** | **Decision & Confidence Model** | Computes status (`COMPLIANT`, `NON_COMPLIANT`, `REVIEW_REQUIRED`, `INSUFFICIENT_DATA`, `NOT_APPLICABLE`), severity, financial exposure, and multi-vector confidence (`data_quality`, `rule`, `overall`). |
| **Layer A6** | **Financial Impact Engine** | Computes quantified risk (`CALCULATED`, `ESTIMATED`, `UNDETERMINED`, `NOT_APPLICABLE`). Never fabricates amounts if data is missing. |
| **Layer B1** | **Exception Management Hub** | Aggregates raw rule failures into business exception categories (Tax, EWB, E-Invoice, ITC, RCM, Data Quality). |
| **Layer B2** | **AI Explanation Layer** | Uses LLM strictly for natural-language explanations, root-cause summaries, vendor risk insights, and Q&A. **LLM cannot override Layer A statutory decisions.** |
| **Layer B3** | **Assisted Resolution & Audit** | Provides human review workflow (`OPEN`, `UNDER_REVIEW`, `ACTION_REQUIRED`, `APPROVED`, `RESOLVED`), advisory SAP action payloads, and immutable audit trails. |

---

## 3. Productization Execution Roadmap (Phases 0–15)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   PRODUCTIZATION EXECUTION ROADMAP                     │
├────────────────────────────────────────────────────────────────────────┤
│ PHASE 0: Repo Audit & Architecture Mapping                             │
│ PHASE 1: Canonical Finance Data Layer with Lineage                     │
│ PHASE 2: Data Quality Engine (Data Usability vs Statutory Failure)      │
│ PHASE 3: Applicability Engine (Filtering Non-Applicable Rules)         │
│ PHASE 4: Core Statutory Engine Alignment & Bug Fixes                   │
│ PHASE 5: Standard Compliance Decision & Multi-Vector Confidence        │
│ PHASE 6: Financial Impact Engine (Quantified vs Undetermined)          │
│ PHASE 7: Exception Management Hub (Business-level Issue Grouping)      │
│ PHASE 8: Root Cause & Cohort Pattern Engine                            │
│ PHASE 9: Finance-Friendly UI (Monitor, Investigate, Reconcile, Audit)   │
│ PHASE 10: AI Agent Layer (Explanation & Inquiry only)                  │
│ PHASE 11: Assisted Resolution & Advisory SAP Payloads                   │
│ PHASE 12: Client Onboarding & Auto-Configuration                       │
│ PHASE 13: Coverage & Audit Reporting                                   │
│ PHASE 14: Rule Dependency Graph                                        │
│ PHASE 15: Comprehensive Test Suite & Scenario Verification             │
└────────────────────────────────────────────────────────────────────────┘
```
