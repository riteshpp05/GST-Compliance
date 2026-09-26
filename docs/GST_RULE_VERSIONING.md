# GST Effective-Date Temporal Resolution & Rule Versioning

## Effective-Date Temporal Matching Rule
Reference resolution evaluates the target transaction date (`invoice_date`) against statutory reference record validity windows:

$$\text{effective\_from} \le \text{invoice\_date} \le (\text{effective\_to} \lor \infty)$$

---

## Resolution Status Outcomes
The `EffectiveDateResolver` produces one of four deterministic outcomes:

1. **`RESOLVED`**: Exactly one active reference record matches the target date.
2. **`NOT_FOUND`**: Zero active reference records match the target date (e.g. transaction date before `effective_from`).
3. **`CONFLICT`**: Greater than one active reference record matches the target date (ambiguous overlap).
4. **`INVALID_REFERENCE`**: Candidate reference record has an inverted date range (`effective_to < effective_from`).

---

## Boundary Testing Matrix

| Boundary Condition | Tested Offset | Expected Status |
| :--- | :--- | :--- |
| **Before Start** | `effective_from - 1 day` | `NOT_FOUND` |
| **Exact Start** | `effective_from` | `RESOLVED` (Version 1) |
| **Inside Window** | `effective_from + 1 day` | `RESOLVED` (Version 1) |
| **Exact Close** | `effective_to` | `RESOLVED` (Version 1) |
| **Next Day** | `effective_to + 1 day` | `RESOLVED` (Version 2) |
