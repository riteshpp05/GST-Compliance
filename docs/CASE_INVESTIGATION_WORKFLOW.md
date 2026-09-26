# UC15 — Case Investigation Workflow

## Executive Summary

This document details the end-to-end investigation workflow for financial and GST tax compliance cases in **UC15 — GST Compliance Intelligence & Resolution Agent**.

---

## Lifecycle States & Workflow Progression

```
+-----------------------------------------------------------------------------------+
| 1. CREATED                    Case initialized from non-compliant invoice or API  |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 2. TRIAGED                    Risk score & priority (P1–P4) assigned              |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 3. INVESTIGATING              Investigator assigned; active review underway       |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 4. EVIDENCE_COLLECTED         Structured evidence (2B, GSTR-1, EWB) attached      |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 5. FINDINGS_READY             Compliance findings recorded with severity          |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 6. RESOLUTION_PROPOSED        Advisory recommendation generated                   |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 7. PENDING_REVIEW             Submitted to Human Review Queue                     |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 8. APPROVED                   Reviewer approves proposed resolution               |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 9. RESOLVED                   Correction executed (vendor notice, GSTR-3B adjust) |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
| 10. CLOSED                    Case archived with full immutable audit history     |
+-----------------------------------------------------------------------------------+
```

---

## Investigation Subsystems Integration

### 1. 4-Way Reconciliation Engine
Compares 4 primary statutory/financial data sources:
- **Purchase Register (ERP)**
- **GSTR-2B (GST Portal Auto-populated)**
- **E-Way Bill (NIC System)**
- **GSTR-3B (Summary Return)**

The workspace matrix presents pair-wise status (`MATCHED`, `DISCREPANCY`, `MISSING`) and flags specific contradiction types (e.g. `TAX_RATE_CONTRADICTION`, `INVOICE_NUMBER_MISMATCH`).

### 2. Evidence Sufficiency Analysis
Rates evidence sufficiency on a 0.0–1.0 scale:
- Evaluates presence of mandatory statutory documents (Invoice copy, GSTR-2B entry, E-Way bill, Proof of Payment).
- Identifies missing evidence items and displays actionable upload targets in the **Missing Evidence** subtab.

### 3. AI Investigation Dossier (6-Part Grounded Report)
Generates a structured, bounded AI investigation report:
1. Executive Summary
2. Compliance Mismatches & Statutory Citations
3. Financial Exposure & Tax Math Trace
4. Grounding & Evidence Citations
5. Recommended Next Steps
6. Confidence & Model Reliability Rating

---

## Statutory Math Trace Modal

Inspectors can click "View Calculation Trace" on any financial exposure card or finding to inspect:
- Formula steps applied.
- Exact statutory provisions (CGST Section 16/17, IGST Section 5).
- Input values, intermediate tax math, and final exposure totals.
