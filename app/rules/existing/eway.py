"""
UC15 GST Compliance Agent — Gate 5: E-Way Bill Compliance Rule (Sprint 4)
Verifies E-Way Bill generation against temporal policy reference thresholds and jurisdiction rules.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.reference.resolvers.effective_date import ResolutionStatus
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext


def _extract_date(d: Optional[object]) -> date:
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(d.strip(), fmt).date()
            except ValueError:
                continue
    return date(2023, 1, 1)


class EWayBillComplianceRule(ComplianceRule):
    """
    Gate 5: Verifies that an E-Way Bill is generated when invoice taxable value exceeds statutory threshold.
    Policy-aware: resolves national and state-specific movement thresholds valid on transaction date.
    Invoices <= threshold are NOT_APPLICABLE.
    """

    @property
    def rule_id(self) -> str:
        return "EWB_001"

    @property
    def name(self) -> str:
        return "E-Way Bill Compliance"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.EWAY_BILL

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    @property
    def gate_no(self) -> int:
        return 5

    @property
    def version(self) -> str:
        return "2.0"

    def validate(
        self,
        invoice: Invoice,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        target_date = _extract_date(invoice.invoice_date)
        gstin = invoice.counterparty_gstin or invoice.gstin
        state_code = gstin[:2] if len(gstin) >= 2 else None

        policy_id = None
        policy_ver = None
        res_status = ResolutionStatus.NOT_FOUND.value
        threshold = float(context.eway_bill_threshold) if context else 50000.0
        pol = None

        # Determine inter-state vs intra-state
        is_interstate = False
        if invoice.igst_rate and float(invoice.igst_rate) > 0:
            is_interstate = True
        elif state_code and invoice.place_of_supply and context and context.reference_service:
            st_res = context.reference_service.resolve_state(state_code, target_date)
            if st_res.is_resolved:
                is_interstate = st_res.record.state_name.strip().lower() != invoice.place_of_supply.strip().lower()

        from app.domain.models.transaction_context import TransactionContext, SupplyCategory
        txn_ctx = getattr(context, "transaction_context", None) or TransactionContext.from_invoice(invoice)

        hsn_str = str(invoice.hsn_code or "").strip()
        is_service = hsn_str.startswith("99") or txn_ctx.category == SupplyCategory.SERVICES

        if is_service:
            reason = "Supply of Services (SAC 99xxxx) does not involve physical transport of goods; E-Way Bill is not applicable under Rule 138."
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NOT_APPLICABLE,
                severity=Severity.INFO,
                category=self.category,
                message=f"E-Way Bill not applicable: {reason}",
                actual_value=hsn_str,
                expected_value="NOT_APPLICABLE for Services",
                observed_value=hsn_str,
                applicability="NOT_APPLICABLE",
                applicability_reason=reason,
                evidence={"hsn_code": hsn_str, "supply_category": "SERVICES"},
                rule_version=self.version,
            )

        if context and context.reference_service:
            res = context.reference_service.resolve_ewb_policy(target_date, state_code=state_code)
            res_status = res.status.value
            if res.status == ResolutionStatus.CONFLICT:
                if context.current_snapshot:
                    context.current_snapshot.record_unresolved(
                        "ewb_policy",
                        state_code or "NATIONAL",
                        res_status,
                        f"E-Way Bill policy conflict on {target_date}",
                    )
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    gate_no=self.gate_no,
                    status=ValidationStatus.NEEDS_REVIEW,
                    severity=self.severity,
                    category=self.category,
                    message=f"E-Way Bill policy conflict: multiple active policies found on {target_date}.",
                    actual_value=None,
                    expected_value="Single unique active policy",
                    applicability="REVIEW",
                    applicability_reason="E-Way Bill policy conflict in reference catalog.",
                    evidence={
                        "resolution_status": res_status,
                        "transaction_date": str(target_date),
                        "state_code": state_code,
                    },
                    rule_version=self.version,
                )
            if res.status == ResolutionStatus.NOT_FOUND:
                if context.current_snapshot:
                    context.current_snapshot.record_unresolved(
                        "ewb_policy",
                        state_code or "NATIONAL",
                        res_status,
                        f"E-Way Bill policy not found for {target_date}",
                    )
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    gate_no=self.gate_no,
                    status=ValidationStatus.NEEDS_REVIEW,
                    severity=self.severity,
                    category=self.category,
                    message=f"E-Way Bill policy not found for transaction date {target_date}.",
                    actual_value=None,
                    expected_value="Active EWB policy",
                    applicability="REVIEW",
                    applicability_reason="E-Way Bill policy not found in reference catalog.",
                    evidence={
                        "resolution_status": res_status,
                        "transaction_date": str(target_date),
                        "state_code": state_code,
                    },
                    rule_version=self.version,
                )

            if res.is_resolved:
                pol = res.record
                policy_id = pol.policy_id
                policy_ver = pol.version
                # FIX 3: Apply jurisdiction-aware threshold (interstate vs intrastate)
                threshold = float(pol.get_threshold_for(is_interstate=is_interstate))

                if context.current_snapshot:
                    context.current_snapshot.set_policy("ewb_policy", pol)

        # FIX 4: Check if HSN is exempt under the resolved policy
        exemption_status = "UNAVAILABLE"
        exemption_reason = "No policy available to evaluate HSN exemption"

        if not invoice.hsn_code:
            exemption_status = "UNAVAILABLE"
            exemption_reason = "Invoice missing HSN code; exemption check unavailable"
        elif pol:
            if pol.is_hsn_exempt(invoice.hsn_code):
                exemption_status = "EXEMPT"
                exemption_reason = f"HSN code '{invoice.hsn_code}' is exempt from E-Way Bill under policy '{policy_id}'"
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    gate_no=self.gate_no,
                    status=ValidationStatus.NOT_APPLICABLE,
                    severity=Severity.INFO,
                    category=self.category,
                    message=f"HSN code '{invoice.hsn_code}' is exempt from E-Way Bill generation under policy '{policy_id}'.",
                    actual_value=invoice.hsn_code,
                    expected_value=f"Exempted HSN in {policy_id}",
                    applicability="NOT_APPLICABLE",
                    applicability_reason=exemption_reason,
                    evidence={
                        "hsn_code": invoice.hsn_code,
                        "exemption_status": exemption_status,
                        "exemption_reason": exemption_reason,
                        "policy_id": policy_id,
                        "reference_version": policy_ver,
                        "resolution_status": res_status,
                        "transaction_date": str(target_date),
                        "taxable_value": float(invoice.taxable_value),
                        "threshold": threshold,
                        "is_interstate": is_interstate,
                        "eway_bill_required": False,
                        "eway_bill_status": invoice.eway_bill_status or "UNSPECIFIED",
                    },
                    rule_version=self.version,
                )
            else:
                exemption_status = "NOT_EXEMPT"
                exemption_reason = f"HSN code '{invoice.hsn_code}' is not in policy '{policy_id}' exemption list"

        taxable_val = float(invoice.taxable_value)
        status = invoice.eway_bill_status
        is_required = taxable_val > threshold

        evidence = {
            "taxable_value": taxable_val,
            "threshold": threshold,
            "is_interstate": is_interstate,
            "eway_bill_required": is_required,
            "eway_bill_status": status or "UNSPECIFIED",
            "eway_bill_number": invoice.eway_bill_number,
            "policy_id": policy_id,
            "reference_version": policy_ver,
            "resolution_status": res_status,
            "transaction_date": str(target_date),
            "hsn_code": invoice.hsn_code,
            "exemption_status": exemption_status,
            "exemption_reason": exemption_reason,
        }

        trace = {
            "taxable_value": taxable_val,
            "threshold": threshold,
            "is_interstate": is_interstate,
            "is_required": is_required,
            "eway_bill_status": status or "UNSPECIFIED",
            "policy_id": policy_id,
            "reference_version": policy_ver,
        }

        if not is_required:
            reason = f"Taxable value Rs.{taxable_val:,.0f} is at or below the Rs.{threshold:,.0f} statutory threshold."
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NOT_APPLICABLE,
                severity=Severity.INFO,
                category=self.category,
                message=reason,
                actual_value=taxable_val,
                expected_value=f"<= Rs.{threshold:,.0f}",
                observed_value=taxable_val,
                applicability="NOT_APPLICABLE",
                applicability_reason=reason,
                reference_id=policy_id,
                reference_version=policy_ver,
                calculation_trace=trace,
                financial_exposure_type="NO_EXPOSURE",
                evidence=evidence,
                rule_version=self.version,
            )

        app_reason = f"Physical movement of goods with taxable value Rs.{taxable_val:,.0f} exceeding Rs.{threshold:,.0f} threshold requires E-Way Bill."

        if status == "GENERATED":
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.PASS,
                severity=Severity.INFO,
                category=self.category,
                message="E-Way Bill generated and valid for this shipment value.",
                actual_value=status,
                expected_value="GENERATED",
                observed_value=status,
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=policy_id,
                reference_version=policy_ver,
                calculation_trace=trace,
                financial_exposure_type="NO_EXPOSURE",
                evidence=evidence,
                rule_version=self.version,
            )

        status_desc = status or "not generated"
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.FAIL,
            severity=self.severity,
            category=self.category,
            message=(
                f"Taxable value Rs.{taxable_val:,.0f} exceeds the "
                f"Rs.{threshold:,.0f} threshold - e-Way Bill status is '{status_desc}'."
            ),
            actual_value=status_desc,
            expected_value="GENERATED",
            observed_value=status_desc,
            applicability="APPLICABLE",
            applicability_reason=app_reason,
            reference_id=policy_id,
            reference_version=policy_ver,
            calculation_trace=trace,
            financial_exposure_type="Potential Exposure",
            evidence=evidence,
            rule_version=self.version,
        )


class EWayBillDistanceValidityRule(ComplianceRule):
    """
    EWB_004: Validates E-Way Bill validity duration based on transport distance and cargo mode.
    Rule 138(10): Normal cargo = 200 km/day; Over-Dimensional Cargo (ODC) = 20 km/day.
    """
    @property
    def rule_id(self) -> str:
        return "EWB_004"

    @property
    def name(self) -> str:
        return "E-Way Bill Distance & Expiry Engine"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.EWAY_BILL

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 5

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        ewb_status = str(invoice.eway_bill_status or invoice.eway_bill or "").upper()
        distance = float(invoice.distance_km or 0.0)
        is_odc = bool(invoice.is_odc)

        if ewb_status == "EXPIRED":
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.HIGH,
                gate_no=self.gate_no,
                message="E-Way Bill has EXPIRED. Movement of goods without valid E-Way Bill attracts penalty under Section 129.",
                evidence={"eway_bill_status": "EXPIRED", "distance_km": distance, "is_odc": is_odc},
                financial_exposure=float(invoice.total_tax),
                version=self.version,
            )

        speed_km_per_day = 20.0 if is_odc else 200.0
        import math
        allowed_days = math.ceil(distance / speed_km_per_day) if distance > 0 else 1

        return ValidationResult.pass_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            gate_no=self.gate_no,
            message=f"E-Way Bill distance validity calculated: {distance} km at {speed_km_per_day} km/day = {allowed_days} day(s) validity.",
            evidence={"distance_km": distance, "is_odc": is_odc, "allowed_days": allowed_days, "speed_km_per_day": speed_km_per_day},
            version=self.version,
        )

