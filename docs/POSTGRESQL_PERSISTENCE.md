# Sprint 14 — PostgreSQL Persistence & Enterprise Data Layer

## 1. Executive Overview

Sprint 14 introduces a production-grade relational persistence layer for `UC15 — GST Compliance Intelligence & Resolution Agent`. 
This layer replaces transient in-memory state for Investigation Sessions, AI Loop Turns, Investigation Cases, Human Review Decisions, Audit Event Timelines, and Evidence Provenance References with a durable relational schema backed by **SQLAlchemy 2.0** ORM models and **Alembic** database migrations.

### Core Architectural Principle
**PostgreSQL/SQLAlchemy is purely a persistence mechanism, NOT a business logic layer.**
All statutory compliance gate checks, risk scoring, financial exposure calculations, root cause analysis, blast radius computations, RAG knowledge retrieval, and case lifecycle state transitions remain 100% authoritative within application domain logic.

---

## 2. Architecture & Design Patterns

```
                               ┌──────────────────────────────────────────────┐
                               │       UC15 Enterprise Domain Layer           │
                               │  (Compliance, Risk, Financial, RAG, Case)    │
                               └──────────────────────┬───────────────────────┘
                                                      │ Domain Models / Enums
                                                      ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       Repository Abstraction Layer                                     │
├──────────────────────────────────────────────────────┬─────────────────────────────────────────────────┤
│                BaseSessionRepository                 │                BaseCaseRepository               │
├──────────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│            SQLAlchemySessionRepository               │            SQLAlchemyCaseRepository             │
│            (or InMemorySessionRepository)            │            (or InMemoryCaseRepository)          │
└──────────────────────────────────────────┬───────────┴─────────────────────────┬───────────────────────┘
                                           │ SQL Transactions                    │
                                           ▼                                     ▼
                               ┌──────────────────────────────────────────────────┐
                               │           SQLAlchemy 2.0 Engine & ORM           │
                               │          (PostgreSQL / SQLite Connection)        │
                               └──────────────────────────┬───────────────────────┘
                                                          │ DDL / Migrations
                                                          ▼
                               ┌──────────────────────────────────────────────────┐
                               │              Alembic Migration Engine            │
                               │           (001_s14_initial_schema.py)            │
                               └──────────────────────────────────────────────────┘
```

### Key Architectural Highlights
1. **Strict Naming & Backend Separation**:
   - Environment variable `PERSISTENCE_BACKEND` controls storage mode (`memory` vs `db` / `sqlalchemy` / `postgres` / `sqlite`).
   - Repository classes are explicitly named `SQLAlchemySessionRepository` and `SQLAlchemyCaseRepository` to avoid mislabeling a SQLite backend as `PostgresRepository`.
   - Repositories implement abstract interfaces `BaseSessionRepository` and `BaseCaseRepository`, guaranteeing zero coupling between application services and database drivers.

2. **Transactional Atomicity**:
   - Case status transitions, human review decisions, and audit timeline events commit atomically within a single `db_session_scope()` transaction block.
   - Rollbacks occur automatically on any unhandled exception, ensuring database state is never left partially updated.

3. **Concurrency Control & Optimistic Locking**:
   - `CaseORM` contains a integer `version` column. Every update increments this version number, preventing lost updates when multiple reviewers interact simultaneously.

4. **100% Round-Trip Fidelity**:
   - Specialized JSON serializer (`app/db/serializer.py`) converts `Decimal` amounts, timezone-aware UTC ISO timestamps (`datetime`), `Enum` strings, `None` values, and nested JSON dictionaries without precision loss.

5. **Immutable Evidence Provenance**:
   - Evidence references (`CaseEvidenceRefORM`) retain exact links to deterministic gate checks (`Gate 1–6`), risk drivers, financial calculations, and regulatory document citations (`DOC-ID`, section numbers, relevance scores).

---

## 3. Relational Schema & Table Definitions

| Table Name | Primary Key | Description | Major Columns / Indexes |
| :--- | :--- | :--- | :--- |
| `investigation_sessions` | `session_id` (String) | Multi-turn investigation session headers | `status`, `entity_focus_json`, `accumulated_findings_json`, `created_at`, `updated_at` |
| `investigation_turns` | `id` (Integer Autoincrement) | Individual turn history per session | `session_id` (FK), `turn_index`, `user_query`, `resolved_query`, `intent`, `tools_used_json`, `synthesized_answer`, `confidence`, `timestamp` |
| `investigation_cases` | `case_id` (String) | Operational Investigation Cases | `title`, `status`, `priority`, `risk_level`, `invoice_id`, `assigned_to`, `financial_exposure`, `root_cause`, `blast_radius_json`, `version` |
| `case_decisions` | `decision_id` (String) | Human review decision records | `case_id` (FK), `reviewer`, `reviewer_role`, `decision`, `comment`, `requested_evidence`, `timestamp` |
| `case_events` | `event_id` (String) | Append-only audit trail timeline | `case_id` (FK), `event_type`, `actor`, `previous_status`, `new_status`, `metadata_json`, `timestamp` |
| `case_evidence_references` | `reference_id` (String) | Immutable evidence citations | `case_id` (FK), `source_type`, `source_identifier`, `invoice_id`, `dossier_id`, `document_id`, `section`, `relevance_score`, `timestamp` |

---

## 4. Configuration & Environment Variables

| Variable | Values | Default | Description |
| :--- | :--- | :--- | :--- |
| `PERSISTENCE_BACKEND` | `memory`, `db`, `sqlalchemy`, `postgres`, `sqlite` | `memory` | Toggles between in-memory repositories and relational DB repositories |
| `DATABASE_URL` | SQLAlchemy URL string | `sqlite:///scratch/uc15_s14.db` | Target database connection URI (e.g. `postgresql+psycopg://user:pass@localhost:5432/uc15_db`) |

---

## 5. Verification & Acceptance Testing

### Primary End-to-End Acceptance Test
Primary process restart survival test: `scratch/verify_s14.py`

#### Workflow Verified:
1. Initialize SQLite database schema (`init_db()`).
2. Create investigation session & run multi-turn AI investigation query.
3. Build investigation dossier & create operational investigation case.
4. Execute human review decision (`CaseDecisionEnum.APPROVE`) with atomic transaction commit.
5. **Simulate Application Process Restart**:
   - Call `reset_db_connection()`.
   - Clear all global repository and service singletons (`_session_manager = None`, `_case_repository = None`, `_case_service = None`).
6. **Verify 100% Data Survival Post-Restart**:
   - Assert session ID, entity focus, turns, and findings survived with 100% fidelity.
   - Assert case status (`READY_FOR_RESOLUTION`), decisions, financial exposure, audit timeline, and evidence references were retrieved cleanly from relational storage.

### Automated Test Suite Execution
- **Dedicated S14 Unit & Integration Tests**: 14 tests passing (`tests/unit/test_database_models.py`, `tests/unit/test_repository_factory.py`, `tests/integration/test_postgres_session_repository.py`, `tests/integration/test_postgres_case_repository.py`, `tests/integration/test_database_migrations.py`).
- **Complete Platform Regression Suite**: 389/389 tests passing (`python tests/run_all_tests.py`).
