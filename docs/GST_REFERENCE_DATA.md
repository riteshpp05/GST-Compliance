# GST Statutory Reference Data Catalog

## Overview
UC15 maintains version-controlled, temporal statutory reference catalogs in structured JSON format under `config/references/`.

---

## Catalog Schemas & Structure

### 1. Tax Rates Schedule (`config/references/tax/tax_rates.json`)
Maps HSN/SAC codes to statutory CGST, SGST, IGST, and Cess percentage rates across effective date windows.
- **`TAX_8471_V1`**: Effective `2017-07-01` to `2025-09-21` (Standard rate schedule).
- **`TAX_8471_V2`**: Effective `2025-09-22` to open-ended (Version 2.0 schedule).

### 2. HSN/SAC Classification Master (`config/references/hsn/hsn_master.json`)
Maintains official Commodity HSN/SAC codes, chapter descriptions, and default rate associations.
- Distinguishes **structural lookup** (`VALID_REFERENCE`, `UNKNOWN_REFERENCE`, `CONFLICTING_REFERENCE`) from legal applicability claims.

### 3. State Code Jurisdiction Master (`config/references/states/state_codes.json`)
Maps 2-digit GSTIN state prefixes (e.g., `29` -> Karnataka, `27` -> Maharashtra, `07` -> Delhi) for Place of Supply intra-state vs inter-state tax structure determination.

### 4. E-Way Bill Policies (`config/references/ewb/ewb_policies.json`)
Maintains national (Rs. 50,000) and state-specific movement value thresholds and exempted commodity lists under Rule 138.

### 5. Section 17(5) ITC Policies (`config/references/itc/itc_policies.json`)
Maintains blocked credit categories (motor vehicles, food & beverages, outdoor catering, membership of clubs) and statutory exception conditions under Section 17(5).
