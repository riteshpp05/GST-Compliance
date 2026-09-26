# UC15 — UI API Contracts & Integrations

## Executive Summary

This document specifies the REST API endpoints and data payloads supporting the Sprint 25 Enterprise UI in **UC15 — GST Compliance Intelligence & Resolution Agent**.

---

## 1. System Readiness & Environment Check

### `GET /ready`
Returns backend health status, active environment mode, database connectivity, and production configuration status.

**Response (200 OK):**
```json
{
  "status": "READY",
  "ready": true,
  "timestamp": "2026-09-15T16:26:21.000Z",
  "details": {
    "environment": "development",
    "persistence_backend": "postgresql",
    "configuration": {
      "valid": true,
      "errors": []
    }
  }
}
```

---

## 2. Dashboard Overview Metrics

### `GET /api/dashboard/overview`
Returns real aggregate KPIs and metrics for the executive dashboard.

**Response (200 OK):**
```json
{
  "kpis": {
    "total_invoices": 34,
    "compliant": 16,
    "needs_review": 10,
    "non_compliant": 8,
    "high_critical_risk": 8,
    "potential_exposure": 92760.0
  },
  "risk_distribution": {
    "LOW": 16,
    "MODERATE": 1,
    "MEDIUM": 9,
    "CRITICAL": 8
  },
  "exposure_summary": {
    "total_exposure": 92760.0,
    "tax_rate_mismatch": 10500.0,
    "itc_at_risk": 82260.0
  }
}
```

---

## 3. Case Review Package Contract

### `GET /api/v1/cases/{case_id}/review-package`
Returns the complete human review package for case workspace rendering.

**Response (200 OK):**
```json
{
  "case_id": "CASE-B96E22A5",
  "title": "Tax rate mismatch on INV-8000001",
  "status": "RESOLUTION_PROPOSED",
  "priority": "P1",
  "risk_level": "CRITICAL",
  "financial_exposure": {
    "additive_total": 10500.0,
    "overlapping_total": 0.0,
    "informational_total": 0.0
  },
  "reconciliation_summary": {
    "overall_status": "DISCREPANCY",
    "match_count": 2,
    "discrepancy_count": 2
  },
  "evidence_sufficiency": {
    "overall_score": 0.85,
    "sufficient": true,
    "missing_items": ["EWAY_BILL_COPY"]
  },
  "ai_dossier_6part": {
    "executive_summary": "...",
    "compliance_mismatches": [],
    "financial_impact": {},
    "grounding_and_citations": [],
    "recommended_next_steps": [],
    "confidence_rating": 0.95
  }
}
```

---

## 4. 4-Way Reconciliation Contract

### `GET /api/v1/cases/{case_id}/reconciliation`
Returns reconciliation pairs across Purchase Register, GSTR-2B, EWB, and GSTR-3B.

**Response (200 OK):**
```json
{
  "case_id": "CASE-B96E22A5",
  "overall_status": "DISCREPANCY",
  "pairs": [
    {
      "source_a": "PURCHASE_REGISTER",
      "source_b": "GSTR_2B",
      "status": "MATCHED",
      "discrepancies": []
    },
    {
      "source_a": "PURCHASE_REGISTER",
      "source_b": "EWAY_BILL",
      "status": "DISCREPANCY",
      "discrepancies": ["TAX_RATE_MISMATCH"]
    }
  ],
  "contradictions": [
    {
      "field": "tax_rate",
      "source_a_value": "18%",
      "source_b_value": "12%",
      "explanation": "Purchase register recorded 18% IGST while E-Way Bill lists 12% IGST."
    }
  ]
}
```

---

## 5. Human Review Decision Submission

### `POST /api/cases/{case_id}/review`
Submits a formal human review decision.

**Request Body:**
```json
{
  "reviewer": "Senior Tax Manager",
  "reviewer_role": "REVIEWER",
  "decision": "APPROVE",
  "comment": "Approved after verifying vendor GSTR-1 correction notice."
}
```

**Response (200 OK):**
```json
{
  "case_id": "CASE-B96E22A5",
  "status": "APPROVED",
  "updated_at": "2026-09-15T16:26:22.000Z"
}
```
