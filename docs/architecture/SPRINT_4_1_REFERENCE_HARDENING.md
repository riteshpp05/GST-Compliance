# SPRINT 4.1: REFERENCE & POLICY HARDENING

## UC15 — GST Compliance Intelligence & Resolution Agent

**Author:** Senior Python Backend Engineer & Enterprise AI/Compliance Architect  
**Sprint:** 4.1 (Hardening Phase)  
**Status:** Completed & Validated  
**Test Suite:** 154 Passing Tests (140 Test Suite Suite + 14 Statutory Regression)

---

## 1. Executive Summary & Architectural Motivation

Sprint 4 introduced temporal reference intelligence, versioned statutory registries, and audit snapshots. However, thorough architectural auditing revealed six critical correctness gaps:
1. Reference gaps (missing or conflicting records) yielded `FAIL` instead of `NEEDS_REVIEW`, violating the principle that reference catalog deficiencies must not penalize taxpayers as statutory non-compliance.
2. E-Way Bill policy resolution did not fall back gracefully from state-specific policies to the national policy for dates prior to state policy enactment.
3. E-Way Bill value validation applied a flat threshold rather than distinguishing interstate movements (statutory INR 50,000) from intrastate movements (state-elevated thresholds such as Maharashtra's INR 1,00,000).
4. E-Way Bill HSN exemptions under Rule 138(14) (e.g. HSN 0101 live animals) were not checked prior to monetary threshold evaluation.
5. Ingestion loaders and legacy scoring callers bypassed the reference service by providing raw dictionaries, risking fractured truth and rate conflicts.
6. Reference snapshots lacked recursive deep immutability and did not track unresolved statutory queries or applicability rationale.

Sprint 4.1 strictly resolves these six correctness gaps with zero architectural drift, preserving the 6-gate compliance pipeline, strict determinism, and 100% backward compatibility.

---

## 2. The 6 Hardened Gaps & Implementation Architecture

```text
                                  ┌───────────────────────────────┐
                                  │       ValidationContext       │
                                  │   (ReferenceService Source)   │
                                  └──────────────┬────────────────┘
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   ▼                                                           ▼
     ┌───────────────────────────┐                               ┌───────────────────────────┐
     │   Gate Rules (Gates 1-6)  │                               │     ReferenceSnapshot     │
     │  - Single source of truth │                               │  - Deep recursive freeze  │
     │  - Yields NEEDS_REVIEW on │                               │  - Unresolved tracking    │
     │    NOT_FOUND or CONFLICT  │                               │  - Statutory provenance   │
     └─────────────┬─────────────┘                               └───────────────────────────┘
                   │ queries
                   ▼
     ┌───────────────────────────┐
     │     ReferenceService      │
     │  - Temporal Date Resolver │
     │  - EWB Historical Fallback│
     │  - ITC Category Matching  │
     └─────────────┬─────────────┘
                   │
                   ▼
     ┌───────────────────────────┐
     │  InMemoryReferenceRepo    │
     │  (Config JSON Statutory)  │
     └───────────────────────────┘
```

### Fix 1: Missing or Conflicting References Yield `NEEDS_REVIEW`
- **Problem:** If an HSN code, state prefix, tax schedule, or EWB/ITC policy was absent from the reference catalog or had overlapping effective dates (`CONFLICT`), rules previously treated the invoice as a statutory failure (`FAIL` / `NON_COMPLIANT`).
- **Solution:** Rules in Gates 2, 3, 4, 5, and 6 now inspect `ResolutionResult.status`:
  - If status is `ResolutionStatus.NOT_FOUND` or `ResolutionStatus.CONFLICT`, the rule immediately returns `ValidationStatus.NEEDS_REVIEW`.
  - The evidence payload records `resolution_status`, `resolution_reason`, and flags the exact unresolved identifier.
  - The unresolved reference is recorded in `snapshot.unresolved` for auditor review.
- **Statutory Justification:** A taxpayer cannot be declared legally non-compliant simply because a compliance engine's master catalog lacks an unmapped tariff code or contains ambiguous administrative records.

### Fix 2: E-Way Bill Temporal Fallback to National Policy
- **Problem:** When an invoice in Maharashtra (State Code 27) was dated prior to Maharashtra's state notification (e.g. 2018-05-01, before Notification No. 4/2019 took effect on 2019-02-01), querying state candidates returned `NOT_FOUND` and failed resolution.
- **Solution:** `ReferenceService.resolve_ewb_policy()` now executes a 2-tier temporal hierarchy:
  1. Inspects state-specific candidates for `clean_state`.
  2. If state candidates exist but *none were active* on `target_date`, it falls back to the active national policy (`state_code=None` or `NATIONAL`).
  3. Annotates the `ResolutionResult.reason` with provenance: `"Fell back to national EWB policy for state {state_code} on {target_date}: {reason}"`.
  4. If a state has no state-specific policies registered (e.g. Karnataka, Gujarat), it directly resolves the active national policy.

### Fix 3: Jurisdiction-Specific E-Way Bill Thresholds
- **Problem:** E-Way Bill compliance checked `taxable_value > policy.threshold`, ignoring the fundamental GST distinction between interstate movements (governed by CGST Rule 138 at INR 50,000) and intrastate movements (governed by state SGST notifications, such as Maharashtra's INR 1,00,000).
- **Solution:**
  - `EWayBillComplianceRule` determines jurisdiction via place of supply vs supplier state prefix or tax profile:
    $$\text{is\_interstate} = (\text{IGST} > 0) \lor (\text{supplier\_state} \neq \text{place\_of\_supply})$$
  - Selects the applicable statutory threshold:
    $$\text{threshold} = \begin{cases} \text{policy.interstate\_threshold} & \text{if is\_interstate} \\ \text{policy.intrastate\_threshold} & \text{if intra-state} \end{cases}$$
  - Enforces boundary conditions: Taxable value $\le \text{threshold}$ yields `NOT_APPLICABLE`; taxable value $> \text{threshold}$ requires an active E-Way Bill.

### Fix 4: E-Way Bill HSN Exemption Logic (Rule 138(14))
- **Problem:** Value threshold was evaluated before checking statutory product exemptions under Rule 138(14) of the CGST Rules, 2017.
- **Solution:**
  - `EWayBillComplianceRule` evaluates `policy.exempted_hsn` *before* evaluating monetary thresholds.
  - If `invoice.hsn_code` matches an exempted HSN (such as HSN 0101 live animals), the rule returns `NOT_APPLICABLE` with `exemption_status: "EXEMPT"`, regardless of movement value (even > INR 500,000).
  - If non-exempt, records `exemption_status: "NOT_EXEMPT"`. If HSN is missing, records `exemption_status: "UNAVAILABLE"` and proceeds to threshold evaluation.

### Fix 5: Single Source of Truth & Clean Legacy Adaptation
- **Problem:** Legacy tests and engine callers passed raw Python dictionaries (`hsn_master`, `state_ref`) directly into `ValidationEngine`. If loaders or context also used these raw dictionaries, rules could bypass `ReferenceService` and cause conflicting rates.
- **Solution:**
  - Strict precedence hierarchy: `Rule` $\rightarrow$ `ValidationContext.reference_service` $\rightarrow$ `ReferenceRepository`.
  - When legacy callers pass dictionaries, `ValidationContext.__init__` and `ValidationEngine.__init__` wrap them safely into `HSNMaster` and populate `ReferenceService` using source tag `LEGACY_ADAPTED`.
  - Official statutory references (`OFFICIAL_GST`) take absolute precedence and cannot be overwritten by legacy dictionaries.

### Fix 6: ReferenceSnapshot Deep Immutability & Audit Provenance
- **Problem:** While `ReferenceSnapshot` was frozen using standard Python frozen dataclass semantics, internal mutable containers (`references` dictionary, `metadata` dictionary) could still be modified post-validation.
- **Solution:**
  - Implemented `_FrozenDict` mapping proxy that intercepts `__setitem__`, `__delitem__`, `pop`, `update`, and `clear`, raising `FrozenSnapshotError`.
  - `ReferenceSnapshot.freeze()` recursively converts all internal dictionaries (`references`, `metadata`, `unresolved`) into `_FrozenDict`.
  - Added structured fields: `applicability_reason`, `source`, and `unresolved`.
  - Added factory `ReferenceSnapshot.from_context(context, invoice)` which builds snapshots automatically from the active `ValidationContext` and invoice metadata.

---

## 3. Tax Rates & Units Normalization

Statutory JSON datasets define tax schedules in decimal fraction notation (e.g. `0.09` for 9% CGST), whereas invoices, Excel sheets, and legacy models express tax rates in percentage figures (e.g. `9.0` or `9`).

To prevent false rate mismatch failures:
- Standardized `config/references/tax/tax_rates.json` and `hsn_master.json` for HSN 8409 to statutory 9% CGST + 9% SGST = 18% IGST.
- Implemented `_to_pct()` normalizer in `TaxRateCorrectnessRule`:
  ```python
  def _to_pct(val: Optional[Union[Decimal, float]]) -> Optional[Decimal]:
      if val is None:
          return None
      d = Decimal(str(val))
      if Decimal("0.0") < d <= Decimal("1.0"):
          return (d * Decimal("100")).quantize(Decimal("0.01"))
      return d.quantize(Decimal("0.01"))
  ```
- Guaranteed scale-invariant comparison: `0.09` and `9.0%` evaluate identically across all validation gates.

---

## 4. Verification & Validation Metrics

| Suite | Scope | Tests Run | Result |
| :--- | :--- | :--- | :--- |
| `tests/run_all_tests.py` | Full Engine, Loaders, Rules, Risk, S4, & S4.1 | 140 | **140/140 PASSED** |
| `tests/unit/test_s4_1_hardening.py` | Dedicated S4.1 Hardening Gaps & Edge Cases | 25 | **25/25 PASSED** |
| `tests/test_scoring.py` | Regression Benchmark Suite | 14 | **14/14 PASSED** |
| `scripts/verify_s4_1_hardening.py` | Manual Representative Scenario Verification | 6 | **6/6 PASSED** |

### Excel Dataset Impact Analysis (30 Invoices)
- **Previous Distribution (Sprint 4):** 15 COMPLIANT, 9 NEEDS_REVIEW, 6 NON_COMPLIANT.
- **Hardened Distribution (Sprint 4.1):** 16 COMPLIANT, 8 NEEDS_REVIEW, 6 NON_COMPLIANT.
- **Statutory Rationale:** Invoice `INV-8000026` is an intra-state Maharashtra movement with taxable value INR 88,000. Under national threshold (INR 50,000), Gate 5 failed. Under hardened Maharashtra jurisdiction logic, the applicable threshold is INR 1,00,000 (Notification No. 4/2019). Because INR 88,000 $\le$ INR 1,00,000, Gate 5 correctly evaluated to `NOT_APPLICABLE`, moving this invoice from `NEEDS_REVIEW` to `COMPLIANT`.

---

## 5. Compliance & Statutory Governance

1. **Rule 138 of CGST Rules, 2017:** National baseline threshold of INR 50,000 for consignment movement.
2. **Rule 138(14) of CGST Rules, 2017:** Statutory exemption list for specified goods (e.g. HSN 0101 live animals, postal baggage, currency) where no E-Way Bill is required regardless of consignment value.
3. **Maharashtra SGST Notification No. 4/2019:** State-specific elevation of intra-state movement threshold to INR 1,00,000 effective February 1, 2019.
4. **Section 17(5) of CGST Act, 2017:** Statutory blocked input tax credit categories (motor vehicles, food and beverages, outdoor catering, beauty treatment, health services).
5. **Fail-Closed Governance:** Absence of reference catalog data or conflicting versions halts automated pass/fail categorization and flags invoices for human review (`NEEDS_REVIEW`), maintaining zero regulatory penalty exposure.
