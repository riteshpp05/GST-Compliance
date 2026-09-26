# Financial Exposure Calculation & Formula Traceability

## Exposure Classification Breakdown
Financial exposure is categorized into distinct, non-overlapping exposure types:

1. **Tax Difference:** Tax rate discrepancy between invoice recorded rate and statutory reference schedule rate.
2. **Potential Exposure:** Shipment value exceeding E-Way Bill threshold without valid EWB status.
3. **ITC at Risk:** Inward input tax credit subject to Section 17(5) blocked credit indicators or missing in GSTR-2B.
4. **Potential Interest:** Statutory interest estimate for delayed or incorrect tax payment.
5. **Potential Penalty:** Statutory penalty estimate for non-compliance.
6. **Actual Liability:** Verified, finalized tax deficiency payable.

---

## Formula Traceability Format
Every financial exposure calculation produces a structured, step-by-step trace record:

```json
{
  "invoice_id": "INV-8000001",
  "rule_id": "TAX_001",
  "exposure_type": "Tax Difference",
  "taxable_value": 100000.00,
  "observed_rate": 0.12,
  "expected_rate": 0.18,
  "rate_delta": 0.06,
  "formula": "taxable_value * (expected_rate - observed_rate)",
  "reference_id": "TAX_8471_V1",
  "reference_version": "1.0",
  "calculated_exposure_inr": 6000.00
}
```
