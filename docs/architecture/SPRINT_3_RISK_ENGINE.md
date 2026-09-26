# SPRINT 3: RISK SCORING & CATEGORIZATION ENGINE

## UC15 — GST Compliance Intelligence & Resolution Agent

**Author:** Senior Backend Engineer & Risk Analytics Architect  
**Sprint:** 3 of 15  
**Status:** Completed & Validated  
**Test Coverage:** 102/102 Tests Passing (88 Unit/Integration + 14 Statutory Regression)

---

## 1. Why the Risk Engine Exists

In enterprise tax compliance and ERP systems (such as SAP FI-Tax), **statutory compliance** is a binary or ternary decision: does this transaction comply with statutory rules, require review, or block return filing?

However, tax directors, compliance officers, and automated audit queues face a fundamental operational challenge:
> **If 100 invoices are marked `NEEDS_REVIEW` or `NON_COMPLIANT`, which ones should be investigated first, how serious is the exposure, what factors drove the risk, and how confident are we in the assessment?**

A flat rule failure count (e.g. `failed_gates * 20`) is dangerous and inaccurate:
- An invoice with a single **CRITICAL** malformed GSTIN or fraudulent supplier blocks filing completely and represents immediate statutory exposure.
- An invoice with two **LOW**-severity documentation warnings (e.g., non-standard date format or minor description variance) may have negligible filing risk.

The **Risk Scoring & Categorization Engine** solves this by evaluating the **nature, severity, statutory category, compounding interactions, and data reliability** of all findings to compute an auditable, deterministic 0–100 risk score and operational priority.

---

## 2. Compliance vs. Risk vs. Severity vs. Financial Exposure

To prevent architectural confusion, Sprint 3 strictly isolates these independent dimensions:

```text
┌───────────────────────────┬──────────────────────────────────────────────────────────────┐
│ Dimension                 │ Core Question & Example                                      │
├───────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 1. Compliance Status      │ "Does this invoice pass statutory requirements?"             │
│                           │ -> COMPLIANT | NEEDS_REVIEW | NON_COMPLIANT                   │
├───────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 2. Finding Severity       │ "How severe is this specific rule violation?"                │
│                           │ -> TAX_001 (HIGH) | GSTIN_001 (CRITICAL) | DATA_002 (MEDIUM) │
├───────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 3. Risk Score & Level     │ "How serious is the business/compliance risk overall?"       │
│                           │ -> Score: 78.0/100 | Level: HIGH                             │
├───────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 4. Investigation Priority │ "How urgently does the operational tax queue need to act?"   │
│                           │ -> P1 (Immediate) | P2 (High) | P3 (Normal) | P4 (Low)       │
├───────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 5. Confidence             │ "How complete and reliable is the supporting evidence?"      │
│                           │ -> HIGH (1.0) | MEDIUM (0.8) | LOW (0.5)                     │
├───────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 6. Financial Exposure     │ "What monetary value is potentially at risk?"                │
│                           │ -> Reserved for Sprint 6 Financial Impact Engine             │
├───────────────────────────┼──────────────────────────────────────────────────────────────┤
│ 7. Anomaly Score          │ "Is this transaction an outlier compared to historical data?"│
│                           │ -> Reserved for Sprint 7 Anomaly Engine                      │
└───────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

## 3. Risk Model Architecture

The target pipeline evaluates risk downstream from compliance decisions without modifying rule evaluation:

```text
DATA INGESTION (Excel, CSV, JSON, Mock)
   │
   ▼
NORMALIZATION (InvoiceNormalizer -> Decimal precision)
   │
   ▼
CANONICAL INVOICE
   │
   ▼
RULE ENGINE 2.0 (Statutory Gates 1–6 + Data Quality DATA_001–005)
   │
   ▼
VALIDATION REPORT (ValidationResult items + structured evidence)
   │
   ▼
DECISION ENGINE (ComplianceDecision: COMPLIANT, NEEDS_REVIEW, NON_COMPLIANT)
   │
   ▼
RISK ENGINE (Sprint 3)
   ├── Severity Contributions (CRITICAL: +40, HIGH: +25, MEDIUM: +15, LOW: +5)
   ├── Category Contributions (TAX: +20, ITC: +20, POS: +15, CLASSIF: +10, etc.)
   ├── Multiple Findings Compounding Penalty (+10 per additional failure)
   ├── Data Quality Adjustments (+5 per DQ failure, capped at 15)
   ├── Policy Overrides & Floors (CRITICAL finding floor = 80.0, Level = CRITICAL, Priority = P1)
   └── Evidence-based Confidence Evaluation (Penalties for missing HSN / unreflected GSTR-2B)
   │
   ▼
RISK ASSESSMENT
   ├── risk_score: 0.0 – 100.0
   ├── risk_level: LOW | MODERATE | MEDIUM | HIGH | CRITICAL
   ├── priority: P1 | P2 | P3 | P4
   ├── confidence: HIGH | MEDIUM | LOW (with confidence_score 0.0–1.0)
   ├── risk_factors: [RiskFactor(...), ...]
   ├── category_scores: {"TAX": 45.0, ...}
   └── explanation: Structured, machine-readable explanation (Zero LLM dependency)
```

---

## 4. Risk Factors & Formula

The risk score is calculated as a bounded, deterministic sum:

$$\text{Raw Score} = \sum \text{Severity Contributions} + \sum \text{Category Contributions} + \text{Multiple Failure Penalty} + \text{Data Quality Impact}$$

$$\text{Bounded Score} = \max(0.0, \min(100.0, \text{Raw Score}))$$

$$\text{Final Score} = \begin{cases} 
\max(\text{Bounded Score}, \text{Floor}_{\text{critical}}) & \text{if CRITICAL finding present} \\
\text{Bounded Score} & \text{otherwise}
\end{cases}$$

### Configured Default Weights
- **Severity**:
  - `CRITICAL`: +40.0
  - `HIGH`: +25.0
  - `MEDIUM`: +15.0
  - `LOW`: +5.0
  - `INFO`: +0.0
  - `WARNING`: 50% factor applied to failure weight
- **Category Base Weights**:
  - `TAX`: +20.0
  - `ITC`: +20.0
  - `PLACE_OF_SUPPLY`: +15.0
  - `CLASSIFICATION`: +10.0
  - `EWAY_BILL`: +10.0
  - `MASTER_DATA`: +5.0
  - `DATA_QUALITY`: +5.0
- **Compounding Multiple Failure Penalty**:
  - +10.0 per additional statutory failure beyond the first failure (capped at +30.0).
- **Data Quality Hygiene Impact**:
  - +5.0 per failed data hygiene rule (capped at +15.0).
- **Critical Finding Floor**:
  - Any statutory finding with `CRITICAL` severity (or Gate 1 hard override) triggers a minimum risk score floor of **80.0**, forces Risk Level to **CRITICAL**, and sets Priority to **P1**.

---

## 5. Risk Levels & Boundary Definitions

Risk levels are mapped through configured, contiguous brackets covering $[0.0, 100.0]$:

| Score Bracket | Risk Level | Description & Operational Response |
|---|---|---|
| **0.0 – 19.99** | `LOW` | Minimal compliance risk. Transaction clean or negligible informational observations. Filing ready. |
| **20.0 – 39.99** | `MODERATE` | Minor documentation issues or low-impact warnings. Standard filing queue. |
| **40.0 – 59.99** | `MEDIUM` | Single high-severity or multiple medium-severity findings. Standard review queue. |
| **60.0 – 79.99** | `HIGH` | Multiple high-severity compliance breaches. 24-hour SLA remediation required. |
| **80.0 – 100.0** | `CRITICAL` | Severe statutory breach (Gate 1 format error, blocked credit, multiple multi-category failures). Mandatory blocker. |

---

## 6. Investigation Priority Classification

Priority separates **operational queue urgency** from pure risk score:
- **`P1` (Immediate)**: Blockers requiring immediate resolution prior to return submission (all CRITICAL risks and Gate 1 failures).
- **`P2` (High)**: Serious findings (HIGH risk items) needing action within current filing cycle (24-hour turnaround).
- **`P3` (Normal)**: Standard findings (MEDIUM risk items) for regular review queue.
- **`P4` (Low)**: Routine items (MODERATE and LOW risk items) processed during standard audits.

---

## 7. Confidence & Evidence Completeness

Confidence measures **how reliable the risk assessment is**, given available data and external evidence:

$$\text{Confidence Score} = 1.0 - \sum \text{Penalties}$$

### Penalty Triggers
- Missing HSN code in Master Catalog: `-0.20`
- AP invoice unreflected in GSTR-2B: `-0.15`
- Data Quality check failures present: `-0.10`
- Missing State code reference: `-0.10`

### Confidence Levels
- **`HIGH`**: Confidence Score $\ge 0.90$ (complete master data and external evidence available).
- **`MEDIUM`**: $0.70 \le \text{Confidence Score} < 0.90$ (minor evidence gaps, e.g. GSTR-2B pending reflection).
- **`LOW`**: Confidence Score $< 0.70$ (critical master catalog missing or severe data hygiene defects).

---

## 8. Externalized Configuration (`config/risk/`)

All risk model parameters live in external YAML configuration files, allowing compliance risk teams to tune weights and policies without touching Python code:

```text
config/
└── risk/
    ├── risk_levels.yaml    # Score ranges: LOW (0-19), MODERATE (20-39), MEDIUM (40-59), HIGH (60-79), CRITICAL (80-100)
    ├── risk_weights.yaml   # Severity weights, category weights, compounding penalty, data quality caps
    └── risk_policy.yaml    # Priority mapping, critical overrides, confidence penalties
```

The [`app.config.risk_config`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/app/config/risk_config.py) module loads these YAML files with resilient fallbacks to code defaults.

---

## 9. Risk Model Versioning

Every [`RiskAssessment`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/app/domain/models/risk.py) records `risk_model_version = "1.0"`.
- If risk weights, category multipliers, or floor policies are modified, the configuration version increments.
- Guarantees historical audits can distinguish whether an invoice score changed due to transaction data changes or risk policy updates.

---

## 10. Future Financial Impact Integration (Sprint 6 Readiness)

[`RiskAssessment.financial_exposure`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/app/domain/models/risk.py) is explicitly modeled as `Optional[Decimal] = None`.
- Sprint 3 **strictly avoids fabricating exposure** (no arbitrary percentage multiplications).
- In Sprint 6, the Financial Impact Engine will inject exact monetary tax exposure, which Risk Engine can incorporate without altering its architecture.

---

## 11. Future Anomaly Detection Integration (Sprint 7 Readiness)

[`RiskAssessment.anomaly_score`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/app/domain/models/risk.py) is modeled as `Optional[float] = None`.
- Sprint 3 remains 100% deterministic and rule-driven.
- In Sprint 7, unsupervised statistical/isolation models can inject an anomaly score into the risk assessment container.

---

## 12. Future Historical Intelligence Integration (Sprint 8 Readiness)

[`RiskAssessment.historical_risk`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/app/domain/models/risk.py) is modeled as `Optional[Dict[str, Any]] = None`.
- Supports future vendor compliance track records, recurring HSN dispute trends, and plant history.

---

## 13. Explainability & Auditability Guarantee

Every non-zero risk score is **100% explainable**:
1. Stored as an explicit list of [`RiskFactor`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/app/domain/models/risk.py) objects.
2. Each factor records: `factor_id`, human-readable `name`, `description`, exact numeric `contribution`, `category`, `severity`, `rule_id`, and underlying `evidence`.
3. The sum of factor contributions (plus any statutory floor) exactly equals the final score.
4. Explanations are synthesized from structured data using deterministic templates. **Zero LLMs or external calls are involved.**

---

## 14. Testing Strategy & Verification

The test suite was expanded with 18 new unit and integration tests:
- [`tests/unit/test_risk_models.py`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/tests/unit/test_risk_models.py): Enums, `RiskFactor`, `RiskAssessment`, `BatchRiskReport` serialization.
- [`tests/unit/test_risk_engine.py`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/tests/unit/test_risk_engine.py):
  - Clean invoice zero risk test.
  - Single low, medium, high, and critical severity tests.
  - Compounding multiple failure penalty test.
  - Data quality and missing evidence confidence tests.
  - Exact boundary tests (0, 19, 20, 39, 40, 59, 60, 79, 80, 100).
  - Determinism verification across repeated evaluations.
  - Full factor sum explainability verification.
  - Dynamic configuration override testing.
- [`tests/integration/test_risk_pipeline.py`](file:///C:/Users/samarth/Downloads/uc15_agent%20%281%29/uc15_agent/tests/integration/test_risk_pipeline.py): End-to-end pipeline execution for Mock, CSV, and Excel with dual persistence in `.xlsx` and `.json`.

```text
======================================================================
  Sprint 3 Test Execution Results
======================================================================
Unit Tests (Models, Rules v2, Checksum, Ingestion, Risk): 82 tests [PASS]
Integration Tests (E2E Pipeline across all formats)     :  6 tests [PASS]
Regression Tests (tests/test_scoring.py)                : 14 tests [PASS]
----------------------------------------------------------------------
Total Tests Executed & Passed                           : 102 / 102 (100%)
======================================================================
```

---

## 15. Known Limitations & Sprint 4 Recommendations

1. **Transaction Value Scaling**: Sprint 3 risk weights are fixed per severity and category; high-value invoices (e.g. ₹50 lakh) currently carry the same risk points as smaller invoices with the same statutory gate failures.
2. **Recommendation for Sprint 4 & 5**: Introduce transaction-value risk scaling and vendor historical compliance profiles in subsequent risk expansions.
