# UC15 — Legacy Code Dependency & Migration Audit (Sprint 20)

## Executive Summary

As part of **Sprint 20 — Architecture Consolidation, Production Integration & Dead-Code Elimination**, a comprehensive dependency audit was conducted across all legacy modules in the root `agent/` directory vs the canonical domain-driven packages in `app/`.

---

## 1. Directory & File Mapping Analysis

| Legacy File (`agent/`) | Canonical Module (`app/`) | Migration Status | Compatibility Function |
|---|---|---|---|
| `agent/gst_compliance_agent.py` | `app/agent/compliance_agent.py` | **MIGRATED (Canonical)** | Main Statutory Pipeline Agent |
| `agent/data_loader.py` | `app/data/loaders/excel_loader.py` | **MIGRATED (Canonical)** | Invoice & Master Data Ingestion |
| `agent/scoring_engine.py` | `app/engines/validation_engine.py` | **MIGRATED (Canonical)** | Gate & Risk Rule Assessment |
| `agent/llm_summary.py` | `app/agent/summary.py` | **MIGRATED (Canonical)** | Executive Summary Formatter |
| `agent/output_writer.py` | `app/agent/output_writer.py` | **MIGRATED (Canonical)** | Excel / JSON Result Exporter |

---

## 2. Dependency Audit & Regression Protection

1. **Production Code Base (`app/`, `ui/`, `main.py`):**
   - 100% of production business endpoints, services, repositories, and UI handlers rely strictly on `app/` modules.
   - Zero production imports reference root `agent/`.

2. **Regression Test Suite (`tests/test_scoring.py`):**
   - `tests/test_scoring.py` contains 50 legacy unit tests validating Sprint 1–3 GSTIN regex and scoring rules.
   - Root `agent/` files are retained as ultra-thin compatibility shims so that `test_scoring.py` runs without breaking historical test contracts.

---

## 3. Preservation & Verification Decision

- **Decision:** Keep root `agent/` as backwards-compatibility wrappers for `test_scoring.py`.
- **Impact:** Zero dead code in production paths; 100% regression suite compatibility maintained.
