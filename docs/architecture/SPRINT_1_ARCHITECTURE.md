# UC15 — GST Compliance Intelligence & Resolution Agent
## Sprint 1 Architecture: Foundation, Architecture & Core Data Contracts

---

### Table of Contents
1. [Overview & Current POC Architecture](#1-overview--current-poc-architecture)
2. [Target Modular Architecture](#2-target-modular-architecture)
3. [Rationale for the Architecture Migration](#3-rationale-for-the-architecture-migration)
4. [Domain Models & Data Contracts](#4-domain-models--data-contracts)
5. [Rule Interface](#5-rule-interface)
6. [Rule Registry](#6-rule-registry)
7. [Validation Engine](#7-validation-engine)
8. [Decision Engine](#8-decision-engine)
9. [End-to-End Data Flow](#9-end-to-end-data-flow)
10. [Configuration Strategy](#10-configuration-strategy)
11. [Testing Strategy](#11-testing-strategy)
12. [Backward Compatibility Matrix](#12-backward-compatibility-matrix)
13. [Future Extension Points (Sprints 2–15)](#13-future-extension-points-sprints-215)

---

### 1. Overview & Current POC Architecture

The initial Proof of Concept (POC) demonstrated a functional 6-gate sequential validation pipeline for Indian GST (Finance / SAP FI-Tax). However, the initial POC had several structural coupling bottlenecks:

* **Monolithic Engine (`agent/scoring_engine.py`)**: Rule definitions, rule evaluation, decision matrix derivation, SAP action mapping, and audit trail generation were all intertwined inside a single class.
* **Loose Data Contracts**: Invoices were loaded as flat, loosely-typed dataclasses (`InvoiceRecord`) using floating-point representations for currency amounts (`taxable_value_inr`, `total_amt`), making them susceptible to floating-point rounding errors.
* **Coupled Business Rules**: The six validation gates were implemented as private methods (`_gate1_...` to `_gate6_...`) inside the engine, making it impossible to add, toggle, or configure individual rules without modifying the engine.
* **Tightly Bound Data Access**: Data parsing, cell slicing from multi-section Excel spreadsheets, and record conversion were tightly coupled inside `agent/data_loader.py`.

---

### 2. Target Modular Architecture

The Sprint 1 refactoring establishes a clean, decoupled, 6-layer architecture with strict separation of concerns:

```text
===================================================================================
                       UC15 ARCHITECTURAL LAYERS
===================================================================================

 [ DATA LAYER ]
  - Raw Sources: Excel (multi-section), CSV, JSON
  - Loaders: BaseInvoiceLoader, ExcelInvoiceLoader, CSVInvoiceLoader, JSONInvoiceLoader
  - Normalization: InvoiceNormalizer (type parsing, dates, Decimal cleanup)
  - Repositories: InvoiceRepository, InMemoryInvoiceRepository
         │
         ▼
 [ DOMAIN MODELS & ENUMS ]
  - Entities: Invoice (Canonical Pydantic), Counterparty, Vendor, Customer
  - Reference: HSNMaster, StateCodeRef, TaxBreakdown, AuditTrail
  - Enums: ComplianceStatus, ValidationStatus, Severity, RuleCategory
  - Contracts: ValidationResult, ValidationReport, ComplianceDecision
         │
         ▼
 [ RULE LAYER ]
  - Base Contract: ComplianceRule (ABC)
  - Registry: RuleRegistry (register, get, all, enabled, by_category)
  - Context: ValidationContext (HSN master, state codes, thresholds)
  - Migrated Rules:
      • Gate 1: GSTINFormatRule (GSTIN_001)       [MASTER_DATA, CRITICAL]
      • Gate 2: HSNValidityRule (HSN_001)         [CLASSIFICATION, HIGH]
      • Gate 3: TaxRateCorrectnessRule (TAX_001)  [TAX, HIGH]
      • Gate 4: PlaceOfSupplyRule (POS_001)       [PLACE_OF_SUPPLY, HIGH]
      • Gate 5: EWayBillComplianceRule (EWB_001)  [EWAY_BILL, MEDIUM]
      • Gate 6: ITCEligibilityRule (ITC_001)      [ITC, HIGH]
         │
         ▼
 [ ENGINE LAYER ]
  - ValidationEngine: Pure rule executor (Invoice + Rules → ValidationReport)
  - DecisionEngine: Compliance classifier (ValidationReport → ComplianceDecision)
         │
         ▼
 [ AGENT & PRESENTATION LAYER ]
  - Orchestrator: GSTComplianceAgent (Perceive → Reason → Act → Learn)
  - Reporting: ResultsWriter (Styled Excel workbook & JSON artifacts)
  - Summary: LLMSummarizer (Heuristic narrative + Optional LLM)
  - Interfaces: CLI (main.py, run.py) & Web UI (FastAPI Checkpoint Dashboard)
         │
         ▼
 [ INFRASTRUCTURE LAYER ]
  - Configuration: AppSettings (Pydantic Settings + .env + Defaults)
  - Logging: Structured logger with sensitive credential protection
===================================================================================
```

---

### 3. Rationale for the Architecture Migration

1. **Extensibility for 40+ Future Rules**: Rules are now discrete, independently testable classes implementing `ComplianceRule`. Future rules (e.g., duplicate detection, circular trading, e-invoice QR verification) can be added without touching the engine.
2. **Financial Precision**: All monetary values and tax percentages have been migrated from raw `float` to `Decimal`, eliminating rounding anomalies in tax rate computations.
3. **Pluggable Ingestion Sources**: By abstracting ingestion behind `BaseInvoiceLoader` and `InvoiceNormalizer`, future sprints can seamlessly connect to SAP S/4HANA (OData/RFC), BigQuery, relational databases, or flat CSVs without modifying core business rules.
4. **Separation of Validation from Decision**: The `ValidationEngine` only evaluates conformance and produces a `ValidationReport`. The `DecisionEngine` determines filing readiness, turnaround SLAs, and SAP corrective actions. This enables future risk scoring and ML models to sit between validation and decision without friction.

---

### 4. Domain Models & Data Contracts

#### 4.1 Canonical Invoice Model (`app/domain/models/invoice.py`)
Strongly-typed Pydantic model enforcing financial validation:
* `invoice_id`: Unique identifier
* `invoice_number`: Canonical invoice number
* `invoice_date`: ISO normalized date (`YYYY-MM-DD`)
* `direction`: "AR" (outward) or "AP" (inward)
* `vendor` / `customer`: Strongly typed `Counterparty` value objects
* `taxable_value`: Monetary amount in `Decimal`
* `cgst_rate`, `sgst_rate`, `igst_rate`, `cess_rate`: Tax rates in `Decimal`
* `total_tax`, `total_amount`: Computed totals in `Decimal`
* `eway_bill`: E-Way Bill lifecycle state
* `gstr2b_reflected`: Boolean flag for counterparty filing reflection
* `metadata`: Extensible dictionary for audit trail and ERP headers

#### 4.2 Standard Result Contract (`app/domain/models/validation.py`)
Every rule produces a standard `ValidationResult`:
```python
ValidationResult(
    rule_id="GSTIN_001",
    rule_name="GSTIN Format Validity",
    status="PASS",                      # PASS | FAIL | WARNING | NOT_APPLICABLE | ERROR
    severity="CRITICAL",                # INFO | LOW | MEDIUM | HIGH | CRITICAL
    category="MASTER_DATA",             # MASTER_DATA | CLASSIFICATION | TAX | POS | EWAY_BILL | ITC
    message="GSTIN 27AAACB1234A1Z5 matches the standard 15-character format.",
    actual_value="27AAACB1234A1Z5",
    expected_value="15-character GSTIN (State+PAN+Entity+Z+Checksum)",
    gate_no=1,                          # Backward compatibility
    name="GSTIN Format Validity",       # Backward compatibility
    detail="..."                         # Backward compatibility
)
```

#### 4.3 Validation Report (`ValidationReport`)
Captures all rule outcomes for an invoice, computing aggregate counts (`passed_count`, `failed_count`, `warning_count`, `not_applicable_count`) and execution timestamp.

#### 4.4 Compliance Decision (`ComplianceDecision`)
The final verdict produced by the `DecisionEngine`:
* `status`: `COMPLIANT`, `NEEDS_REVIEW`, `NON_COMPLIANT`, or `BLOCKED`
* `failed_gate_count`: Total number of failing checks
* `justification`: Detailed audit justification
* `recommended_action`: Operational next steps for the tax team
* `sap_action`: Direct SAP posting or hold instruction
* `audit_trail_ref`: Traceable identifier (e.g. `GST-A1B2C3D4E5`)
* `hard_override`: True if a fatal gate (e.g. malformed GSTIN) failed

---

### 5. Rule Interface

The `ComplianceRule` abstract base class governs all rule implementations:

```python
class ComplianceRule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def category(self) -> RuleCategory: ...

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    @property
    def enabled(self) -> bool:
        return True

    @abstractmethod
    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult: ...
```

---

### 6. Rule Registry

The `RuleRegistry` manages rule registration, discovery, and filtering:
* `register(rule: ComplianceRule)`: Registers a rule.
* `get(rule_id: str)`: Looks up a rule by ID.
* `all()`: Returns all registered rules.
* `enabled()`: Returns all rules where `rule.enabled == True`.
* `by_category(category: RuleCategory)`: Filters rules by functional category.
* `create_default_registry()`: Factory pre-registering the 6 core GST rules.

---

### 7. Validation Engine

The `ValidationEngine` is a pure rule runner:
1. Accepts an `Invoice` (or batch of invoices).
2. Retrieves all active rules from the registry.
3. Executes each rule with `ValidationContext` (providing HSN master data, state references, and thresholds).
4. Catches unhandled rule exceptions gracefully, converting them into `ValidationStatus.ERROR` results without crashing the batch.
5. Returns a structured, JSON-serializable `ValidationReport`.

---

### 8. Decision Engine

The `DecisionEngine` evaluates the `ValidationReport` against the GST compliance policy:
* **Gate 1 Fail** $\rightarrow$ `NON_COMPLIANT` (Hard Override: malformed GSTIN prevents filing).
* **0 Failures** $\rightarrow$ `COMPLIANT` (Ready for GSTR-1/GSTR-3B filing).
* **1 Failure** $\rightarrow$ `NEEDS_REVIEW` (Same-cycle turnaround SLA of 24h).
* **2+ Failures** $\rightarrow$ `NON_COMPLIANT` (Blocked from return filing, SLA of 4h).

---

### 9. End-to-End Data Flow

```text
+-------------------+
| Excel / CSV / JSON|
+-------------------+
          │
          ▼
+---------------------+
| BaseInvoiceLoader   | (Loads raw sections/rows)
+---------------------+
          │
          ▼
+---------------------+
|  InvoiceNormalizer  | (Cleans nulls, formats dates, parses Decimal)
+---------------------+
          │
          ▼
+---------------------+
|  InvoiceRepository  | (Stores and indexes canonical Invoices)
+---------------------+
          │
          ▼
+---------------------+
|  ValidationEngine   | <--- [ValidationContext] (HSN Master, State Codes)
+---------------------+ <--- [RuleRegistry] (GSTIN_001, HSN_001, TAX_001, etc.)
          │
          ▼
+---------------------+
|  ValidationReport   | (Passed: 5, Failed: 1, Warnings: 0, N/A: 0)
+---------------------+
          │
          ▼
+---------------------+
|   DecisionEngine    | (Evaluates policy, generates SAP action & audit ref)
+---------------------+
          │
          ▼
+---------------------+
| ComplianceDecision  | (Status: NEEDS_REVIEW, Audit: GST-1234567890)
+---------------------+
          │
          ├────────────────────────┬────────────────────────┐
          ▼                        ▼                        ▼
+-------------------+    +--------------------+    +------------------+
|   ResultsWriter   |    |   LLMSummarizer    |    |   FastAPI UI     |
| (Excel & JSON)    |    | (Executive report) |    | (Checkpoint dot) |
+-------------------+    +--------------------+    +------------------+
```

---

### 10. Configuration Strategy

Centralized settings via `app/config/settings.py` and `app/config/defaults.py`:
* **Environment Configuration**: Loaded from `.env` via `python-dotenv` and strongly-typed via `AppSettings`.
* **Safe Defaults**: All parameters have fallback defaults; secrets are never hardcoded.
* **Controlled Hardcoded + Configurable**:
  * Thresholds: `EWAY_BILL_THRESHOLD_INR = 50,000`
  * Tolerances: `RATE_TOLERANCE_PCT = 0.01`
  * Blocked Categories: `DEFAULT_ITC_BLOCKED_KEYWORDS` (Section 17(5))
  * SLAs: `NEEDS_REVIEW_SLA_HOURS = 24`, `NON_COMPLIANT_SLA_HOURS = 4`
* **Template Provided**: `.env.example` includes placeholders for all configurable variables.

---

### 11. Testing Strategy

The test suite provides comprehensive coverage across all layers:
1. **Unit Tests (`tests/unit/`)**:
   * `test_models.py`: Canonical invoice construction, Decimal precision, missing optional fields, model serialization.
   * `test_rules.py`: Positive and negative test cases for each of the 6 migrated rules; registry registration and category filtering.
   * `test_normalization.py`: Raw row parsing, date formats (`YYYY-MM-DD`, `DD-MM-YYYY`), null string handling, Decimal conversion.
   * `test_engines.py`: `ValidationEngine` reporting, error handling for crashing rules, `DecisionEngine` classification matrix.
2. **Integration Tests (`tests/integration/`)**:
   * `test_pipeline.py`: Full end-to-end run against `data/UC15_GSTCompliance_Dataset.xlsx`, verifying the exact distribution (15 Compliant, 9 Needs Review, 6 Non-Compliant).
3. **Regression Tests (`tests/test_scoring.py`)**:
   * All 14 original POC tests run completely unmodified and pass.
4. **Master Test Runner (`tests/run_all_tests.py`)**:
   * Executes all 59 tests in a single command.

---

### 12. Backward Compatibility Matrix

| Original Component | New Location | Compatibility Strategy |
|---|---|---|
| `config/settings.py` | `app/config/settings.py` | Legacy `config/settings.py` re-exports all constants directly. |
| `agent/data_loader.py` | `app/data/loaders/excel_loader.py` | Preserved `InvoiceRecord`, `HSNMaster`, `StateCodeRef`, `UC15DataLoader`. |
| `agent/scoring_engine.py` | `app/rules/` & `app/engine/` | Legacy `ValidationEngine` wraps the modular engines and rules. |
| `agent/gst_compliance_agent.py` | `app/agent/compliance_agent.py` | Re-exports `GSTComplianceAgent`. |
| `agent/output_writer.py` | `app/agent/output_writer.py` | Re-exports `ResultsWriter`. |
| `agent/llm_summary.py` | `app/agent/summary.py` | Re-exports `LLMSummarizer`. |
| `run.py` | `run.py` & `main.py` | CLI flags (`--invoice`, `--ui`) preserved and working identically. |
| `ui/app.py` | `ui/app.py` | FastAPI dashboard runs against the modular agent without changes. |

---

### 13. Future Extension Points (Sprints 2–15)

* **Sprint 2 (Data Ingestion & ERP Connectors)**: Implement SAP S/4HANA OData and RFC connectors into `app/data/loaders/`.
* **Sprint 3 (Extended GST Rule Library)**: Add rules `GSTIN_002` through `GSTIN_010`, `HSN_002`+, circular trade rules into `app/rules/`.
* **Sprint 4 (Risk Scoring & Financial Exposure)**: Implement risk weighting and tax exposure calculation in `app/engine/risk_engine.py`.
* **Sprint 5 (Anomaly & Fraud Detection)**: Connect statistical and ML models via `app/engine/anomaly_engine.py`.
* **Sprint 6 (Resolution Agent & SAP Workflow Automation)**: Implement automated remediation actions in `app/agent/resolution_agent.py`.
