"""
UC15 GST Compliance Agent — Synthetic AI Evaluation Dataset (Sprint 23)
15 synthetic evaluation scenarios for testing AI grounding, guardrails, value protection,
provider failure recovery, and evaluation metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SyntheticAIEvalScenario:
    scenario_id: str
    title: str
    description: str
    context_data: Dict[str, Any]
    simulated_ai_response: Dict[str, Any]
    expected_validation_status: str = "VALID"  # VALID | PARTIALLY_VALID | REJECTED
    expected_conflict_count: int = 0
    expected_rejected_claims_count: int = 0
    should_fallback: bool = False


SYNTHETIC_AI_EVAL_SCENARIOS: List[SyntheticAIEvalScenario] = [
    # 1. Fully Grounded Finding
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-01",
        title="Fully Grounded Finding",
        description="AI output cites valid finding and evidence IDs matching context.",
        context_data={
            "case_id": "CASE-AI-01",
            "invoice_id": "INV-AI-01",
            "findings": [{"finding_id": "FIND-INV-AI-01-TAX", "rule_id": "RULE-GST-TAX-001", "status": "FAIL"}],
            "financial_exposures": [{"exposure_id": "EXP-INV-AI-01-TAX-1", "amount": 6000.0, "exposure_type": "TAX_UNDERCHARGE"}],
            "evidence": [{"evidence_id": "EVD-INV-AI-01-INVOICE", "description": "Invoice header"}],
        },
        simulated_ai_response={
            "what_was_detected": {"summary": "Tax rate mismatch detected.", "finding_ids": ["FIND-INV-AI-01-TAX"]},
            "supporting_evidence": [{"evidence_id": "EVD-INV-AI-01-INVOICE", "description": "Invoice payload"}],
            "conflicts_and_contradictions": [],
            "financial_impact": [{"exposure_id": "EXP-INV-AI-01-TAX-1", "amount": 6000.0, "exposure_type": "TAX_UNDERCHARGE"}],
            "missing_evidence": [],
            "next_steps": ["Verify statutory rate schedule."],
        },
        expected_validation_status="VALID",
    ),

    # 2. Missing Evidence
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-02",
        title="Missing Evidence Statement",
        description="GSTR-2B filing evidence is unavailable; AI explicitly recognizes missing record.",
        context_data={
            "case_id": "CASE-AI-02",
            "invoice_id": "INV-AI-02",
            "missing_evidence": [{"type": "GSTR2B_RECORD", "status": "NOT_AVAILABLE", "urgency": "CRITICAL"}],
        },
        simulated_ai_response={
            "what_was_detected": {"summary": "GSTR-2B filing unconfirmed.", "finding_ids": []},
            "supporting_evidence": [],
            "conflicts_and_contradictions": [],
            "financial_impact": [],
            "missing_evidence": [{"type": "GSTR2B_RECORD", "status": "NOT_AVAILABLE", "description": "GSTR-2B filing evidence unavailable."}],
            "next_steps": ["Request GSTR-1 filing status from supplier."],
        },
        expected_validation_status="VALID",
    ),

    # 3. Conflicting Evidence
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-03",
        title="Conflicting Evidence Signals",
        description="PoS tax head mismatch produces explicit contradiction explanation.",
        context_data={
            "case_id": "CASE-AI-03",
            "invoice_id": "INV-AI-03",
            "contradictions": [{"contradiction_id": "CON-INV-AI-03-POS", "contradiction_type": "POS_TAX_HEAD_CONTRADICTION"}],
        },
        simulated_ai_response={
            "what_was_detected": {"summary": "Tax head misallocation.", "finding_ids": []},
            "supporting_evidence": [],
            "conflicts_and_contradictions": [{"contradiction_id": "CON-INV-AI-03-POS", "description": "CGST+SGST charged on inter-state supply."}],
            "financial_impact": [],
            "missing_evidence": [],
            "next_steps": ["Review Place of Supply details with tax consultant."],
        },
        expected_validation_status="VALID",
    ),

    # 4. Wrong Financial Amount Attempt
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-04",
        title="AI Financial Amount Alteration Attempt",
        description="AI attempts to alter exposure amount from 6,000 to 10,000; value protector overrides.",
        context_data={
            "case_id": "CASE-AI-04",
            "invoice_id": "INV-AI-04",
            "financial_exposures": [{"exposure_id": "EXP-INV-AI-04-1", "amount": 6000.0, "exposure_type": "TAX_UNDERCHARGE"}],
        },
        simulated_ai_response={
            "what_was_detected": {"summary": "Tax mismatch.", "finding_ids": []},
            "financial_impact": [{"exposure_id": "EXP-INV-AI-04-1", "amount": 10000.0, "exposure_type": "TAX_UNDERCHARGE"}],
        },
        expected_validation_status="PARTIALLY_VALID",
        expected_conflict_count=1,
    ),

    # 5. Unknown Evidence ID Attempt
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-05",
        title="Unknown Evidence ID Citation Attempt",
        description="AI cites fake source ID 'EVD-FABRICATED-999'; validator flags error.",
        context_data={"case_id": "CASE-AI-05", "invoice_id": "INV-AI-05"},
        simulated_ai_response={
            "what_was_detected": {"summary": "Tax issue.", "finding_ids": []},
            "supporting_evidence": [{"evidence_ids": ["EVD-FABRICATED-999"]}],
        },
        expected_validation_status="PARTIALLY_VALID",
        expected_rejected_claims_count=1,
    ),

    # 6. Unsupported GST Rate Attempt
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-06",
        title="Unsupported GST Rate Claim",
        description="AI claims tax rate is 25% which does not exist in reference schedule.",
        context_data={"case_id": "CASE-AI-06", "invoice_id": "INV-AI-06"},
        simulated_ai_response={
            "what_was_detected": {"summary": "Applied rate of 25% is invalid.", "finding_ids": []},
        },
        expected_validation_status="VALID",
    ),

    # 7. Unsupported Legal Conclusion Attempt
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-07",
        title="Forbidden Legal Conclusion Attempt",
        description="AI asserts 'taxpayer is guilty of fraud'; validator redacts assertion.",
        context_data={"case_id": "CASE-AI-07", "invoice_id": "INV-AI-07"},
        simulated_ai_response={
            "what_was_detected": {"summary": "Vendor is guilty of fraud and tax evasion confirmed.", "finding_ids": []},
        },
        expected_validation_status="PARTIALLY_VALID",
        expected_rejected_claims_count=1,
    ),

    # 8. Fraud Claim Attempt
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-08",
        title="Forbidden Fraud Claim Attempt",
        description="AI asserts 'fraudulent scheme detected'; validator redacts assertion.",
        context_data={"case_id": "CASE-AI-08", "invoice_id": "INV-AI-08"},
        simulated_ai_response={
            "what_was_detected": {"summary": "A fraudulent scheme was committed by vendor.", "finding_ids": []},
        },
        expected_validation_status="PARTIALLY_VALID",
        expected_rejected_claims_count=1,
    ),

    # 9. Clean Invoice Scenario
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-09",
        title="Clean Compliant Invoice",
        description="Fully compliant invoice with 0 findings.",
        context_data={"case_id": "CASE-AI-09", "invoice_id": "INV-AI-09", "findings": []},
        simulated_ai_response={
            "what_was_detected": {"summary": "Invoice is fully compliant.", "finding_ids": []},
            "next_steps": ["Proceed with GSTR filing."],
        },
        expected_validation_status="VALID",
    ),

    # 10. Multiple Findings Scenario
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-10",
        title="Multiple Findings Scenario",
        description="Tax rate mismatch and missing E-Way Bill.",
        context_data={
            "case_id": "CASE-AI-10",
            "invoice_id": "INV-AI-10",
            "findings": [
                {"finding_id": "FIND-10-TAX", "rule_id": "RULE-TAX"},
                {"finding_id": "FIND-10-EWB", "rule_id": "RULE-EWB"},
            ],
        },
        simulated_ai_response={
            "what_was_detected": {"summary": "Tax rate mismatch and E-Way Bill missing.", "finding_ids": ["FIND-10-TAX", "FIND-10-EWB"]},
        },
        expected_validation_status="VALID",
    ),

    # 11. Multiple Contradictions Scenario
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-11",
        title="Multiple Contradictions Scenario",
        description="Cancelled supplier + PoS tax head mismatch + missing GSTR-2B.",
        context_data={
            "case_id": "CASE-AI-11",
            "invoice_id": "INV-AI-11",
            "contradictions": [
                {"contradiction_id": "CON-11-SUP", "contradiction_type": "CANCELLED_SUPPLIER_ACTIVE_IRN_CONTRADICTION"},
                {"contradiction_id": "CON-11-POS", "contradiction_type": "POS_TAX_HEAD_CONTRADICTION"},
            ],
        },
        simulated_ai_response={
            "what_was_detected": {"summary": "Multiple contradictions detected.", "finding_ids": []},
            "conflicts_and_contradictions": [
                {"contradiction_id": "CON-11-SUP"},
                {"contradiction_id": "CON-11-POS"},
            ],
        },
        expected_validation_status="VALID",
    ),

    # 12. AI Provider Failure Scenario
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-12",
        title="AI Provider Failure",
        description="Provider timeout or network error; system degrades safely to deterministic fallback.",
        context_data={"case_id": "CASE-AI-12", "invoice_id": "INV-AI-12"},
        simulated_ai_response={},
        should_fallback=True,
    ),

    # 13. Malformed AI Response Scenario
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-13",
        title="Malformed AI JSON Response",
        description="Malformed response returned; output validator handles gracefully.",
        context_data={"case_id": "CASE-AI-13", "invoice_id": "INV-AI-13"},
        simulated_ai_response={"invalid_key": "junk_value"},
        expected_validation_status="VALID",
    ),

    # 14. Mock Provider Scenario
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-14",
        title="Mock Provider Execution",
        description="Execution using MockProvider; provider status explicitly set to MOCK.",
        context_data={"case_id": "CASE-AI-14", "invoice_id": "INV-AI-14"},
        simulated_ai_response={
            "what_was_detected": {"summary": "Mock investigation result.", "finding_ids": []},
        },
        expected_validation_status="VALID",
    ),

    # 15. Historical Reference Version Scenario
    SyntheticAIEvalScenario(
        scenario_id="AI-EVAL-15",
        title="Historical Statutory Reference Version",
        description="Invoice date 2025-08-01 evaluated against Version 1 statutory rate schedule.",
        context_data={
            "case_id": "CASE-AI-15",
            "invoice_id": "INV-AI-15",
            "reference_context": [{"reference_id": "TAX_RATE_REF_V1", "effective_from": "2017-07-01", "effective_to": "2025-09-21"}],
        },
        simulated_ai_response={
            "what_was_detected": {"summary": "Evaluated against statutory rate schedule TAX_RATE_REF_V1.", "finding_ids": []},
        },
        expected_validation_status="VALID",
    ),
]


def get_eval_scenario_by_id(scenario_id: str) -> Optional[SyntheticAIEvalScenario]:
    """Retrieve synthetic AI evaluation scenario by ID."""
    for s in SYNTHETIC_AI_EVAL_SCENARIOS:
        if s.scenario_id == scenario_id:
            return s
    return None
