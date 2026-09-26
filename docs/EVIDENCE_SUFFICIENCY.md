# UC15 GST Compliance Agent — Evidence Sufficiency & Missing Evidence Evaluator

## Overview

Sprint 22 implements an **Evidence Sufficiency Evaluator** (`app/investigation/evidence/sufficiency_evaluator.py`) to systematically assess the completeness of investigation evidence for any case or invoice.

---

## Evidence Sufficiency States

- **`SUFFICIENT`** (Score ≥ 0.90): Evidence is complete across all statutory, filing, and master data dimensions for conclusive resolution.
- **`PARTIALLY_SUFFICIENT`** (0.60 ≤ Score < 0.90): Key records available, but essential statutory items (e.g. GSTR-2B or IRN) are unconfirmed.
- **`INSUFFICIENT`** (0.0 < Score < 0.60): Multiple critical records missing; investigation cannot conclude cleanly.
- **`NOT_AVAILABLE`** (Score = 0.0): Zero evidence records attached to case.

---

## Missing Evidence Urgency Levels

| Urgency | Criteria | Impact |
| :--- | :--- | :--- |
| **`CRITICAL`** | Raw invoice payload missing, or GSTR-2B entry missing on AP purchase invoice | Directly blocks statutory ITC claim and invoice verification |
| **`HIGH`** | Supplier GSTIN master status unverified or IRN e-invoice missing on high-value B2B invoice | Risk of transacting with cancelled entity or non-compliant e-invoicing |
| **`MEDIUM`** | E-Way Bill missing for consignment > INR 50,000 | Transport movement verification under Rule 138 incomplete |
| **`LOW`** | Supplementary ERP metadata or non-critical item descriptions missing | Informational only |

---

## API Endpoints

- `GET /api/v1/cases/{case_id}/review-package` (includes `evidence_sufficiency` summary and missing items checklist)
