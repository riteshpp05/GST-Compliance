# SPRINT 5: HISTORICAL INTELLIGENCE & TIME-SERIES AUDIT

## UC15 — GST Compliance Intelligence & Resolution Agent

**Author:** Senior Python Backend Engineer & Enterprise AI/Compliance Architect  
**Sprint:** 5 (Historical Intelligence & Time-Series Audit Phase)  
**Status:** Completed & Validated  
**Test Suite:** 188 Passing Tests (174 Unit & Integration Tests + 14 Statutory Regression Tests)  

---

## 1. Objective

The primary objective of Sprint 5 is to transition the UC15 GST Compliance Agent from answering single-transaction compliance queries:
> **"Is this invoice compliant?"**

to answering systemic, multi-dimensional, longitudinal questions across invoices, counterparties, rules, periods, and time:
> **"What has been happening across invoices, vendors, rules, periods, and time?"**

Sprint 5 introduces a deterministic historical intelligence layer that analyzes previously processed compliance decisions and identifies:
* **Repeated compliance failures:** Rules and checks that fail across multiple invoices and periods.
* **Recurring rule violations:** Trajectory of specific statutory failures (persistent, emerging, improving, resolved, isolated).
* **Vendor/customer compliance patterns:** Longitudinal counterparty compliance rates, recurring anomalies (e.g. same vendor + same HSN + same wrong tax rate).
* **Period-over-period trends:** Quantitative rate changes (improving, stable, deteriorating, insufficient data) across daily, weekly, monthly, and quarterly windows.
* **Repeated data-quality problems:** Separating operational data hygiene (missing state, invalid GSTIN format, omitted fields) from statutory non-compliance.
* **Retroactive audit results:** Re-evaluating historical transactions under effective-date-aware reference intelligence and comparing outcomes (same result, changed result, reference changed, newly compliant, newly non-compliant, previously unresolved).
* **Deterministic, explainable evidence:** Full lineage from aggregated findings back to underlying transactions and raw invoices without AI hallucinations or non-deterministic heuristics.

---

## 2. Architecture

The architecture preserves strict separation of concerns across the processing pipeline:

```text
Data Source (Excel, CSV, JSON, Mock, SAP)
                ↓
    Normalization & Ingestion
                ↓
        Canonical Invoice
                ↓
   Six-Gate Rule Validation Engine
                ↓
         Decision Engine
                ↓
           Risk Engine
                ↓
       Compliance Decisions
                ↓
┌────────────────────────────────────────────────────────┐
│             HISTORICAL INTELLIGENCE LAYER              │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │               HistoricalService                  │  │
│  │  - Primary orchestration facade                  │  │
│  │  - Repository storage & query                    │  │
│  └──────────────────────┬───────────────────────────┘  │
│                         │                              │
│       ┌─────────────────┼─────────────────┐            │
│       ▼                 ▼                 ▼            │
│  ┌───────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  Period   │   │    Trend    │   │Rule Pattern │     │
│  │ Analyzer  │   │  Analyzer   │   │  Analyzer   │     │
│  └───────────┘   └─────────────┘   └─────────────┘     │
│       │                 │                 │            │
│       ▼                 ▼                 ▼            │
│  ┌───────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │Counterprty│   │Data Quality │   │ Historical  │     │
│  │ Analyzer  │   │  Analyzer   │   │AuditAnalyzer│     │
│  └───────────┘   └─────────────┘   └─────────────┘     │
│                         │                              │
│                         ▼                              │
│                 HistoricalReport                       │
│      - Period Metrics & Aggregations                   │
│      - Period-over-Period Trends                       │
│      - Rule Failure Patterns & Lineage                 │
│      - Counterparty Longitudinal Profiles              │
│      - Systemic & Counterparty DQ Defects              │
│      - Retroactive Simulation Outcomes                 │
└────────────────────────────────────────────────────────┘
```

### Architectural Responsibilities:
* **Compliance Engine:** What happened on this transaction? (Deterministic Six-Gate statutory rules).
* **Historical Intelligence:** What pattern exists across transactions over time? (Time-series aggregations, trends, recurrence).
* **Risk Engine:** How severe and impactful is the transaction issue? (Financial impact, vendor risk weight, regulatory urgency).
* **Future AI Agent:** What should the compliance team or user do about it? (Action orchestration, vendor dispute resolution, filing adjustments).

---

## 3. Historical Data Model

Historical Intelligence consumes validated `ComplianceDecision` instances and optional source `Invoice` entities to construct a normalized, immutable `HistoricalRecord`. Re-running statutory rules during aggregation is strictly avoided.

### Schema: `HistoricalRecord`
```python
@dataclass
class HistoricalRecord:
    invoice_id: str
    invoice_date: date
    direction: str = "AR"                  # "AR" (Sales) | "AP" (Purchases)
    supplier_gstin: str = ""
    supplier_name: str = ""
    customer_gstin: str = ""
    customer_name: str = ""
    counterparty_gstin: str = ""
    counterparty_name: str = ""
    place_of_supply: str = ""
    hsn_code: str = ""
    item_desc: str = ""
    taxable_value: Decimal = Decimal("0.00")
    total_tax: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")

    # Compliance Verdict & Gate Results
    compliance_status: str = "COMPLIANT"   # COMPLIANT | NEEDS_REVIEW | NON_COMPLIANT
    failed_gate_count: int = 0
    failed_rule_ids: List[str] = field(default_factory=list)
    failed_gate_numbers: List[int] = field(default_factory=list)
    gate_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Data Quality findings
    data_quality_findings: List[str] = field(default_factory=list)

    # Risk Engine outcomes
    risk_level: Optional[str] = None       # LOW | MODERATE | MEDIUM | HIGH | CRITICAL
    risk_priority: Optional[str] = None    # P1 | P2 | P3 | P4
    risk_score: Optional[float] = None
    confidence: Optional[float] = None

    # Reference intelligence versions active when evaluated
    reference_versions: Dict[str, str] = field(default_factory=dict)
    unresolved_references: Dict[str, Any] = field(default_factory=dict)

    # Audit lineage
    audit_trail_ref: str = ""
    evaluated_at: str = field(default_factory=...)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

Direct property accessors (`transaction_type`, `validation_status`, `failed_gates`) provide compatibility with legacy and statutory audit terminology.

---

## 4. Period Aggregation

Deterministic time grouping is performed across four standard temporal intervals:
1. **DAILY:** `YYYY-MM-DD` (Operational reconciliation).
2. **WEEKLY:** `YYYY-Www` (ISO calendar week, e.g. `2026-W24`).
3. **MONTHLY:** `YYYY-MM` (Primary statutory GST filing interval, e.g. GSTR-1 / GSTR-3B).
4. **QUARTERLY:** `YYYY-Q#` (Composition scheme and QRMP filing interval, e.g. `2026-Q2`).

### Aggregated Metrics (`PeriodMetrics`)
For each discrete time bucket:
* Total volume: $N = \text{total\_invoices}$
* Status counts: $C_{\text{compliant}}, C_{\text{needs\_review}}, C_{\text{non\_compliant}}$
* Statutory rates:
  $$\text{compliance\_rate} = \frac{C_{\text{compliant}}}{N} \times 100$$
  $$\text{needs\_review\_rate} = \frac{C_{\text{needs\_review}}}{N} \times 100$$
  $$\text{non\_compliance\_rate} = \frac{C_{\text{non\_compliant}}}{N} \times 100$$
* Financial aggregates: $\sum \text{taxable\_value}$, $\sum \text{total\_tax}$, $\sum \text{total\_amount}$
* Failure tallies: Total failed gate instances, failure counts indexed by `rule_id` and `gate_no`
* Data lineage: Chronological list of invoice IDs contributing to the period bucket.

---

## 5. Trend Methodology

Sequential period-over-period comparisons calculate exact percentage point deltas and relative velocity:
$$\Delta_{\text{pp}} = \text{rate}_{t} - \text{rate}_{t-1}$$
$$\Delta_{\%} = \frac{\text{rate}_{t} - \text{rate}_{t-1}}{\text{rate}_{t-1}} \times 100 \quad (\text{if } \text{rate}_{t-1} > 0)$$

### Deterministic Trend Classification
Thresholds are externalized in `HistoricalConfig`:
* **IMPROVING:** $\Delta_{\text{pp}} \ge +5.0\text{ pp}$
* **DETERIORATING:** $\Delta_{\text{pp}} \le -5.0\text{ pp}$
* **STABLE:** $-5.0\text{ pp} < \Delta_{\text{pp}} < +5.0\text{ pp}$
* **INSUFFICIENT_DATA:** When fewer than 2 periods exist, or when invoice volume in either period is below `min_period_invoices_for_trend` (default: 1).

No subjective or generative descriptions are generated; explanations cite the exact prior period, current period, percentage point change, and base rates.

---

## 6. Rule Pattern Methodology

Rule failure trajectories are classified deterministically by tracking failure frequencies across chronological periods.

```text
                     Rule Failure Pattern Decision Logic
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
      Prior Failures > 0                              Prior Failures == 0
     Latest Failures == 0                                     │
              │                                               ▼
              ▼                                        Latest Failures >= 2
          RESOLVED                                            │
                                                              ▼
                                                           EMERGING
              │
              ├─ Failure count decreasing by >= 25% ─────────► IMPROVING
              │
              ├─ Consecutive failures in >= 2 periods ───────► PERSISTENT
              │
              └─ Sporadic failure (< 2 occurrences) ──────────► ISOLATED
```

### Classification Categories:
1. **PERSISTENT:** The rule failed across consecutive periods ($\ge \text{persistent\_consecutive\_periods}$, default: 2) and exceeds minimum pattern occurrences ($\ge 2$).
2. **EMERGING:** The rule was absent or low historically but surged significantly in the latest period ($\ge \text{emerging\_min\_latest\_failures}$, default: 2, and $\ge 1.5\times$ prior average or previous period count).
3. **IMPROVING:** Failure frequency is decreasing significantly (reduction ratio $\ge 25\%$ between adjacent periods).
4. **RESOLVED:** The rule previously exhibited recurring failures but recorded exactly 0 failures in the latest period.
5. **ISOLATED:** Sporadic failure not meeting systemic multi-period recurrence thresholds.

Lineage is strictly preserved: each `RuleFailurePattern` lists all `affected_invoices`, `periods_observed`, and period-by-period count maps.

---

## 7. Counterparty Analysis

Counterparty intelligence builds longitudinal behavioral profiles for suppliers (AP) and customers (AR).

### Profile Attributes (`CounterpartyProfile`):
* `counterparty_id`, `counterparty_name`, `gstin`, `direction`
* Volume metrics: `total_invoices`, `compliant_count`, `needs_review_count`, `non_compliant_count`, `compliance_rate`
* Failure metrics: `total_failures`, `top_failed_rules` (ranked `(rule_id, count)` tuples)
* Temporal coverage: `first_transaction_date`, `last_transaction_date`, `periods_active`
* Trajectory: `recent_trend` (`IMPROVING`, `STABLE`, `DETERIORATING` based on performance across active periods)
* Traceable transactions: `affected_invoices`.

### Counterparty Consistency Patterns (`RecurringCounterpartyPattern`)
Systemic vendor habits are identified when a counterparty repeats the identical statutory defect across transactions:
* **Example:** Vendor ABC repeatedly applies 12% GST to HSN 8471 (where statutory tariff is 18%) across multiple periods.
* Identified by grouping records on `(counterparty_id, hsn_code, failed_rule_id)`.
* Emits a `RECURRING_COUNTERPARTY_PATTERN` with explicit evidence containing the rule, tariff code, observed values, and underlying invoice keys.

---

## 8. Data-Quality Analysis

To ensure data-entry defects do not obscure or masquerade as statutory tax evasion, data defects are partitioned into dedicated `DataQualityPattern` entities.

### Tracked Data Defect Types:
* `INVALID_GSTIN_FORMAT`: Malformed GSTINs failing structure or checksum.
* `INVALID_INVOICE_DATE`: Unparseable, null, or out-of-bounds dates.
* `MISSING_STATE_INFO`: Unspecified state code or name for parties.
* `MISSING_PLACE_OF_SUPPLY`: Omitted statutory supply jurisdiction.
* `MISSING_COUNTERPARTY_GSTIN`: Blank or missing counterparty tax ID.
* `MISSING_HSN_CODE`: Missing mandatory tariff classification.
* `MISSING_INVOICE_ID`: Missing invoice identification number.

### Analysis Dimensions:
1. **Systemic Ingestion Defects:** Cross-transaction occurrences across periods with frequency rates.
2. **Counterparty-Specific Defect Ratios:** Flagging vendors where $\ge 20\%$ of submitted invoices suffer from data quality omissions (e.g. "Vendor XYZ omits Place of Supply on 40% of invoices").

---

## 9. Retroactive Audit / Simulation

The retroactive audit capability tests historical transactions against the statutory reference catalog applicable on their original transaction dates, rather than contemporary rules.

```text
Recorded Historical Record
(Invoice Date: 2020-06-15)
           │
           ▼
Resolve Historical Reference Data
(Effective Date Resolver: 2020-06-15)
           │
           ▼
Execute Statutory Rules & Decision
           │
           ▼
Compare Recorded Result vs Retroactive Result
           │
           ├── Verdicts identical? ──────────────► SAME_RESULT
           │
           ├── Reference version changed? ────────► REFERENCE_CHANGED
           │
           ├── Was NEEDS_REVIEW, now decided? ───► PREVIOUSLY_UNRESOLVED
           │
           ├── Was NON_COMPLIANT, now COMPLIANT? ─► NEWLY_COMPLIANT
           │
           └── Was COMPLIANT, now NON_COMPLIANT? ─► NEWLY_NON_COMPLIANT
```

### Audit Outcomes:
* `SAME_RESULT`: Retroactive evaluation confirms original verdict.
* `RESULT_CHANGED`: Compliance status shifted between runs.
* `PREVIOUSLY_UNRESOLVED`: Incomplete historical data or unmapped reference was subsequently resolved by historical reference updates.
* `NEWLY_COMPLIANT`: Transaction originally deemed failing is upgraded to compliant under the actual historical rule (e.g. intra-state movement under state-elevated EWB notification).
* `NEWLY_NON_COMPLIANT`: Transaction previously deemed compliant fails under tightened historical reference.
* `REFERENCE_CHANGED`: Compliance verdict identical, but underlying reference record versions advanced.

---

## 10. Evidence and Lineage

Every finding emitted by the historical intelligence layer contains deterministic lineage:
$$\text{Invoice} \longrightarrow \text{ComplianceDecision} \longrightarrow \text{HistoricalRecord} \longrightarrow \text{Period / Pattern Aggregation} \longrightarrow \text{Finding}$$

No synthetic aggregates are produced without back-pointers:
* Every `PeriodMetrics` contains the full list of constituent `invoices`.
* Every `RuleFailurePattern` contains the exact `affected_invoices` and `period_counts`.
* Every `CounterpartyProfile` contains `affected_invoices`.
* Every `RecurringCounterpartyPattern` contains `affected_invoices` and observable statutory fields.
* Every `DataQualityPattern` lists `affected_invoices`.
* Every `HistoricalAuditComparison` references the `invoice_id`, original gate failures, retroactive gate failures, and version diffs.

---

## 11. Threshold / Configuration Strategy

All pattern and trend logic is governed by `HistoricalConfig`:

| Configuration Field | Default | Statutory / Mathematical Rationale |
|---|---|---|
| `trend_improving_threshold_pp` | `+5.0` pp | Filters random volume variance from genuine compliance improvement |
| `trend_deteriorating_threshold_pp` | `-5.0` pp | Meaningful drop in filing readiness requiring intervention |
| `min_period_invoices_for_trend` | `1` | Prevents zero-division; allows small-batch unit testing |
| `min_pattern_invoices` | `2` | Guarantees an isolated occurrence is never flagged as systemic |
| `min_pattern_periods` | `2` | Establishes multi-period longitudinal recurrence |
| `persistent_consecutive_periods` | `2` | Confirms unbroken consecutive failure across reporting periods |
| `emerging_growth_factor` | `1.5` | Surge threshold ($+50\%$ over historical baseline) |
| `emerging_min_latest_failures` | `2` | Prevents single low-volume glitches from triggering emerging alert |
| `improving_reduction_ratio` | `0.25` | Requires $\ge 25\%$ decrease in failure frequency |
| `counterparty_recurring_min_failures`| `2` | Minimum repetitions from one vendor on same issue |
| `counterparty_high_failure_rate_pct` | `30.0%` | High-risk vendor threshold |
| `dq_min_occurrences` | `2` | Repeated operational hygiene threshold |
| `dq_counterparty_affected_ratio` | `0.20` | Flags vendor if $\ge 20\%$ of invoices have data defects |

---

## 12. Test Coverage

The Sprint 5 test suite is comprehensive and verified green:
* **Master Runner (`tests/run_all_tests.py`):** 188 total tests (174 unit/integration + 14 regression).
* **Dedicated Unit Suite (`tests/unit/test_historical_intelligence.py`):** 34 tests covering:
  1. *Period Aggregation:* Daily, weekly, monthly, quarterly.
  2. *Compliance Metrics:* 100% compliant, mixed population, 100% non-compliant, 100% needs-review, empty dataset.
  3. *Trend Analysis:* Improving, stable, deteriorating, insufficient data.
  4. *Rule Patterns:* Persistent, emerging, improving, resolved, isolated.
  5. *Counterparty Intelligence:* Single vendor, multi-vendor, unknown/missing identity, recurring vendor patterns.
  6. *Data Quality:* Recurring defect, isolated defect, clean dataset.
  7. *Historical Audit:* Same result, changed result, reference changed, previously unresolved.
  8. *Boundary Cases:* 0 invoices, 1 invoice, 1 period, 2 periods, missing dates (None handling), missing counterparty, duplicate invoice ID updates, full field serialization.
* **Manual Verification (`scripts/verify_s5_historical_intelligence.py`):** 8/8 end-to-end scenarios passing.

---

## 13. Limitations

* **Repository Implementation:** The default repository is `InMemoryHistoricalRepository`. While supporting sub-millisecond lookups via inverted indexes, production persistence will require SQL/NoSQL storage adapters implementing `BaseHistoricalRepository`.
* **Out-of-Order Ingestion:** When invoices arrive out of chronological order, the in-memory repository re-sorts automatically upon aggregation; however, streaming sliding-window state machines are deferred to pipeline scaling sprints.
* **Vendor Disambiguation:** Counterparties with subtle spelling variations in legal names without a GSTIN are grouped under their raw string. Entity resolution belongs to a future master data deduplication sprint.

---

## 14. Future Integration with AI Agent

In subsequent sprints, the AI Agent will consume `HistoricalReport` as a structured, deterministic observation layer:
1. **Explainable Prompts:** Instead of querying raw transactions, the agent receives pre-aggregated findings (e.g. *"Rule TAX_001 has been PERSISTENT for Vendor ABC across May–July with 38 failures"*).
2. **Automated Vendor Notices:** The agent can draft targeted discrepancy letters referencing recurring HSN and rate mismatch evidence.
3. **Filing Readiness Recommendations:** The agent can advise the tax controller on expected reconciliation adjustments before monthly GSTR filing based on historical trends.
4. **Resolution Strategy:** High-confidence automated corrections for systemic data quality issues (e.g. populating missing state codes from vendor GSTIN prefixes).
