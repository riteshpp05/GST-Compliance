# UC15 — Canonical Production Architecture (v2.0 / Sprint 20 Consolidated)

## Overview

The **UC15 GST Compliance Intelligence & Resolution Agent** is an enterprise-grade, agentic AI-driven statutory tax compliance, anomaly detection, risk intelligence, and human-in-the-loop investigation platform.

---

## 1. System Architecture & Component Model

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                            User Interfaces                              │
 │   Command Line (main.py)              FastAPI Dashboard (ui/app.py)     │
 └────────────────────┬───────────────────────────────────┬────────────────┘
                      │                                   │
 ┌────────────────────▼───────────────────────────────────▼────────────────┐
 │                      Authentication & RBAC Layer                        │
 │     AuthenticationService / get_current_principal (Header Auth & RBAC)  │
 └────────────────────┬───────────────────────────────────┬────────────────┘
                      │                                   │
 ┌────────────────────▼───────────────────────────────────▼────────────────┐
 │                 Statutory & Anomaly Intelligence Engine                 │
 │  Data Ingestion -> Quality Engine -> Gate Validation -> Risk Engine     │
 │  Financial Exposure -> Duplicate/Anomaly Intelligence -> Root Cause     │
 └────────────────────┬───────────────────────────────────┬────────────────┘
                      │                                   │
 ┌────────────────────▼───────────────────────────────────▼────────────────┐
 │                    Agentic AI Investigation Subsystem                   │
 │   AIInvestigationAgent (Tool Selector, Planner, Executor, Evaluator)   │
 └────────────────────┬───────────────────────────────────┬────────────────┘
                      │                                   │
 ┌────────────────────▼───────────────────────────────────▼────────────────┐
 │                   Case Management & Human Authorization                 │
 │   CaseService -> CaseStateMachine (Human-in-the-Loop Decision Gate)     │
 └────────────────────┬───────────────────────────────────┬────────────────┘
                      │                                   │
 ┌────────────────────▼───────────────────────────────────▼────────────────┐
 │                     Persistence & Database Subsystem                    │
 │   SQLAlchemy 2.0 Repositories (CaseRepo, SessionRepo, DataQualityRepo)   │
 └─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. End-to-End Data Pipeline Flow

1. **Ingestion & Data Quality Gate (Sprint 17):**
   - Ingests ERP / Excel / CSV / JSON records.
   - Evaluates 6 quality dimensions (`COMPLETENESS`, `VALIDITY`, `CONSISTENCY`, `UNIQUENESS`, `ACCURACY`, `TIMELINESS`).
   - Produces deterministic `DataQualityReport` and persists via `SQLAlchemyDataQualityRepository`.

2. **Normalization & Statutory Validation (Sprints 1–3):**
   - Normalizes GSTINs, state codes, dates, and currency values.
   - Validates 30+ statutory GST rules (ITC eligibility, GSTR-2B reflection, E-Way bill validity, Place of Supply, Tax Rate correctness).

3. **Risk & Financial Impact Assessment (Sprints 3 & 6):**
   - Calculates risk scores (0–100) and risk priority levels (P1–P4).
   - Computes tax exposure, interest penalties, and ITC at risk.

4. **Anomaly & Duplicate Intelligence (Sprints 10–11):**
   - Identifies candidate duplicate clusters and statistical transaction anomalies.
   - Computes candidate root causes and blast radius exposure.

5. **Agentic AI Investigation (Sprint 12):**
   - Controlled `AIInvestigationAgent` executes evidence-first investigation tool loops across 19 registered read-only tools.
   - Produces investigation traces, evidence packages, and AI decision recommendations.

6. **Case Management & Human Approval Workflow (Sprints 13–15):**
   - `CaseService` manages formal investigation cases.
   - `CaseStateMachine` strictly enforces that **AI CANNOT RESOLVE OR APPROVE CASES**.
   - Authorized Human Reviewers submit review decisions (`APPROVE`, `REJECT`, `REQUEST_MORE_EVIDENCE`).

7. **Relational Persistence & Audit Trail (Sprints 14–19):**
   - Full persistence across application restarts using SQLAlchemy 2.0 models (`CaseORM`, `SessionORM`, `DataQualityORM`).
   - Immutable audit logging and event timeline tracking (`CaseEvent`).

---

## 3. Entry Points & Usage Contracts

- **Canonical Batch Execution:**
  ```bash
  python main.py --file data/raw/sample_invoices.csv
  ```

- **Canonical Production Web Application:**
  ```bash
  python main.py --ui
  ```

- **Execution Mode Security:**
  - `APP_ENV=production`: Enforces mandatory header-based authentication on all business endpoints (`X-API-Key` or `Authorization`).
  - `APP_ENV=development`: Permits local developer UI fallback for unauthenticated browser sessions.

---

## 4. Route Security Classification Summary

- **Total FastAPI Routes:** 91
- **Protected Business Endpoints:** 78 (Secured via `Depends(get_current_principal)`)
- **Public Infrastructure Endpoints:** 13 (`/health`, `/ready`, `/live`, `/api/health`, `/api/ready`, `/api/live`, `/docs`, `/openapi.json`, `/redoc`, `/`, `/api/knowledge/status`)
