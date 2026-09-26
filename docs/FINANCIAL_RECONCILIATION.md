# UC15 GST Compliance Agent — Financial Record Reconciliation & Contradiction Detection

## Overview

Sprint 22 introduces a **Multi-Way Financial Record Reconciliation & Contradiction Detection Engine** (`app/reconciliation/`) for UC15. This engine connects invoice data, statutory tax calculations, GSTR-2B filing statements, and ERP supplier master records into a unified, explainable 4-way comparison matrix.

---

## 4-Way Reconciliation Dimensions

| Dimension | Source A | Source B | Status Options | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`INVOICE_VS_TAX_CALC`** | Invoice Taxable Value & Tax Charged | Deterministic Statutory Tax Calculation | `MATCH`, `MISMATCH`, `NOT_AVAILABLE` | Compares declared tax against effective-date statutory rate schedule. |
| **`INVOICE_VS_GSTR2B`** | Invoice Taxable Value & Total Tax | GSTR-2B Auto-Populated Filing Statement | `MATCH`, `MISMATCH`, `NOT_AVAILABLE` | Validates buyer's Section 16(2)(aa) ITC eligibility against supplier GSTR-1 filings. |
| **`INVOICE_VS_SUPPLIER_ERP`** | Supplier GSTIN & Legal Name | Vendor ERP Master Record | `MATCH`, `MISMATCH`, `NOT_AVAILABLE` | Verifies vendor active registration status and payment details. |
| **`INVOICE_VS_TAX_PERIOD`** | Invoice Transaction Date | Statutory Filing Window | `MATCH`, `NOT_AVAILABLE` | Verifies transaction date falls within allowed filing tax period. |

---

## Cross-Signal Contradiction Types

1. **`POS_TAX_HEAD_CONTRADICTION` (Severity: CRITICAL)**
   - **Trigger:** Intra-State tax (CGST + SGST) charged when Supplier State != Recipient State / Place of Supply.
   - **Statutory Impact:** Section 77 CGST / Section 19 IGST misallocation of tax head.

2. **`CANCELLED_SUPPLIER_ACTIVE_IRN_CONTRADICTION` (Severity: CRITICAL)**
   - **Trigger:** Invoice issued by supplier with GSTIN status `CANCELLED` or `SUSPENDED` prior to transaction date.
   - **Statutory Impact:** Section 16(2)(a) violation; invalid tax invoice issued by non-registered entity.

3. **`ERP_PAID_GSTR2B_MISSING_CONTRADICTION` (Severity: HIGH)**
   - **Trigger:** Payment marked `PAID` in buyer ERP, but invoice missing from buyer GSTR-2B statement.
   - **Statutory Impact:** Section 16(2)(aa) ITC risk; cash remitted to vendor but input credit unreflected.

4. **`EFFECTIVE_DATE_TAX_RATE_CONTRADICTION` (Severity: HIGH)**
   - **Trigger:** Invoice rate differs from statutory rate schedule version in effect on transaction date.
   - **Statutory Impact:** Under/overcharging of statutory tax.

---

## API Endpoint

- `GET /api/v1/cases/{case_id}/reconciliation`
