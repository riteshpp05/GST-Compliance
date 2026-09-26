# UC15 — Finance Review & Human Approval Workflow

## Executive Summary

Sprint 25 enforces strict human review and safety controls for finance and tax decisioning in **UC15 — GST Compliance Intelligence & Resolution Agent**. Automated AI agents are restricted to advisory recommendations; terminal resolution requires explicit human review.

---

## Review Queue & Decision Controls

When a case reaches `RESOLUTION_PROPOSED` or `PENDING_REVIEW`, it appears in the Human Review Queue. Reviewers inspect the unified `HumanReviewPackage` containing:
- Executive Summary & Findings
- Financial Exposure Breakdown & Math Trace
- 4-Way Reconciliation Matrix
- AI Investigation Dossier & Grounding
- Evidence Sufficiency Score

---

## Review Decision Options

Reviewers must select one of 4 explicit decisions:

1. **APPROVE**: Approves the proposed resolution recommendation (e.g. issuing credit note, vendor tax adjustment, or GSTR-3B table 4(D) ITC reversal).
2. **REJECT**: Rejects the proposed resolution; requires mandatory rationale explanation.
3. **REQUEST_MORE_EVIDENCE**: Transitions case back to `MORE_EVIDENCE_REQUIRED`; specifies exact document artifacts required.
4. **RETURN_FOR_INVESTIGATION**: Transitions case back to `INVESTIGATING` with specific instructions for the investigator.

---

## Safety & Governance Safeguards

- **Decision Confirmation Modal**: Prevent accidental submissions by presenting a confirmation modal summarizing decision impact.
- **Mandatory Audit Comment**: A non-empty comment explaining the financial rationale is required for all review decisions.
- **Role-Based Authorization**: Only users with `REVIEWER` or `ADMIN` role can submit decisions via `/api/cases/{case_id}/review`.
- **Immutable Audit Trail**: All decisions are recorded in the case timeline with actor name, timestamp, correlation ID, and decision metadata.
