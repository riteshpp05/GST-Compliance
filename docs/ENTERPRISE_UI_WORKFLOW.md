# UC15 — Enterprise UI Workflow Architecture

## Executive Summary

Sprint 25 transforms the UI layer of **UC15 — GST Compliance Intelligence & Resolution Agent** into a canonical, role-aware, finance-investigator-oriented enterprise application. It replaces fragmented demo panels with a unified 10-tab Case Investigation Workspace, real-time dashboard metrics, statutory calculation trace viewers, and a 10-state case lifecycle engine with human review safety boundaries.

---

## Key Architecture & Components

```
+----------------------------------------------------------------------------------------------------+
|                                    ENTERPRISE UI SHELL (index.html)                                 |
|  +-------------------------------------+  +-------------------------+  +------------------------+  |
|  | Runtime Environment Indicator Badge |  | RBAC Active Role Switch |  | User Profile Indicator |  |
|  +-------------------------------------+  +-------------------------+  +------------------------+  |
+----------------------------------------------------------------------------------------------------+
                                                  |
       +------------------------------------------+------------------------------------------+
       |                                          |                                          |
       v                                          v                                          v
+-----------------------------+    +-----------------------------+    +------------------------------+
|     EXECUTIVE DASHBOARD     |    |    CASE MANAGEMENT LIST     |    |  CASE INVESTIGATION WORKSPACE|
|  - Real backend metrics     |    |  - Lifecycle filters        |    |  - 10-State Lifecycle Stepper|
|  - Financial exposure summary|   |  - Exposure ranges          |    |  - 10 Dedicated Subtabs      |
|  - Readiness & health status|    |  - Severity & evidence status|   |  - Math Trace Viewer Modal   |
+-----------------------------+    +-----------------------------+    +------------------------------+
```

### 1. Unified 10-Tab Case Workspace

The workspace provides 10 dedicated subtabs grounded in Sprint 20–24 backend intelligence:

1. **Overview**: Executive summary, key metadata, risk priority, and lifecycle state.
2. **Findings**: Formal compliance mismatches, severity breakdown, and statutory rule citations.
3. **Financial Exposure**: Exposure breakdown (Additive, Overlapping, Informational) with direct access to calculation traces.
4. **Evidence**: Evaluated evidence records, document metadata, hash signatures, and sufficiency scores.
5. **4-Way Reconciliation**: Direct 4-way record matching matrix comparing Purchase Register, GSTR-2B, E-Way Bill, and GSTR-3B.
6. **Contradictions**: Discovered evidence contradictions, source conflicts, and reliability weightings.
7. **AI Investigation Dossier**: Bounded 6-part AI dossier (Executive Summary, Compliance Mismatches, Financial Impact, Grounding & Citations, Recommended Next Steps, Confidence Rating).
8. **Missing Evidence**: Identified missing document types and required statutory artifacts for resolution.
9. **Case Timeline**: Chronological event audit log tracking status transitions and system actions.
10. **Audit Log**: Immutable audit records, actor IDs, correlation IDs, and timestamped decision traces.

---

## 10-State Case Lifecycle Stepper

The Case Workspace features a visual 10-state lifecycle progress bar tracking the lifecycle of an investigation:

```
[1. CREATED] -> [2. TRIAGED] -> [3. INVESTIGATING] -> [4. EVIDENCE_COLLECTED] -> [5. FINDINGS_READY]
  -> [6. RESOLUTION_PROPOSED] -> [7. PENDING_REVIEW] -> [8. APPROVED] -> [9. RESOLVED] -> [10. CLOSED]
```

- States are strictly enforced by the backend `CaseStateMachine`.
- Automated AI agents cannot approve or resolve cases.
- Transitioning to terminal states (`APPROVED`, `RESOLVED`, `CLOSED`) requires authorized human intervention with mandatory audit comments.

---

## Statutory Calculation Trace Viewer Modal

Whenever financial exposure or tax calculation math is presented, the UI allows inspectors to open a step-by-step statutory tax math trace modal:

- Displays taxable value, applied tax rates (CGST, SGST, IGST, Cess), expected vs actual amounts.
- Cites statutory provisions (e.g. CGST Act Section 16(2), Section 17(5)).
- Displays deterministic formula traces with zero hidden math or ungrounded statistics.

---

## Verification & Integrity

- **Zero Fake Statistics**: All metrics on the dashboard and case lists are fetched directly from `/api/dashboard/overview`, `/api/v1/cases`, and `/ready`.
- **RBAC Header Binding**: Active role selections in the header dynamically inject authorization headers (`X-API-Key` or `X-User-Role`) for backend validation.
- **Environment Isolation**: Runtime Environment Shell Indicator clearly flags `DEMO / SYNTHETIC DATA`, `TEST ENVIRONMENT`, or `PRODUCTION ENVIRONMENT`.
