# UC15 — Role-Based UI Controls & Authorization

## Executive Summary

Sprint 25 introduces role-aware UI controls in **UC15 — GST Compliance Intelligence & Resolution Agent**. The UI dynamically adapts action buttons, workspace tabs, and review controls based on the active user profile, while relying strictly on backend RBAC enforcement for security.

---

## Supported Roles & UI Permissions

| Role | UI Capabilities | Dynamic UI Controls Enabled |
| :--- | :--- | :--- |
| **INVESTIGATOR** | Investigates cases, collects evidence, adds findings, and proposes recommendations. | "Start Investigation", "Add Evidence", "Record Finding", "Propose Recommendation" |
| **REVIEWER** | Reviews case packages, evaluates recommendations, and executes human approval/rejection. | "Approve Case", "Reject Case", "Request More Evidence", "Return for Investigation" |
| **AUDITOR** | Inspects compliance cases, statutory calculation traces, 4-way reconciliation, and audit logs. | Read-only inspection across all workspace tabs, calculation trace modals, and audit logs. |
| **ADMIN** | Full system access including configuration, performance benchmarks, and user role management. | All actions enabled, including case assignment, re-triage, and system configuration. |

---

## Role Switcher Architecture

- Located in the top navigation bar of `ui/templates/index.html`.
- Allows users and testers to select active profile (`INVESTIGATOR`, `REVIEWER`, `AUDITOR`, `ADMIN`).
- Persists selected role in `sessionStorage` and attaches `X-User-Role` / `X-API-Key` to every API request sent by `ui/static/js/api.js`.

---

## Security Boundary & Fail-Closed Enforcement

> [!IMPORTANT]
> **Client-Side UI Hiding is NOT Security.**
> The backend authorization middleware (`app.security.auth`) remains authoritative. If an unauthorized user attempts to trigger an API action (e.g. an `INVESTIGATOR` calling `/api/cases/{id}/review`), the backend returns `403 Forbidden` regardless of UI state.

---

## UI Error Handling for RBAC

- **401 Unauthorized**: Redirects user to login or prompts credential update; displays environment authentication banner.
- **403 Forbidden**: Displays an inline permission denial alert with exact permission required (e.g. `CASE_REVIEW` required).
- **Graceful Control Disabling**: Action buttons are disabled or hidden in the UI when the active role lacks the corresponding permission.
