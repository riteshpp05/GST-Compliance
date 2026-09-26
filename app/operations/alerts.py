"""
app.operations.alerts
=====================
Operational Alert Evaluator for UC15 (Sprint 19).
Evaluates system metrics, cases, data quality, and evaluation runs to generate
actionable operational alerts without generating noisy alerts for normal events.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from app.infrastructure.logging import get_logger
from app.operations.models import AlertCategoryEnum, AlertSeverityEnum, OperationalAlert

logger = get_logger(__name__)


class OperationalAlertEvaluator:
    """
    Evaluates system indicators and constructs actionable operational alerts.
    """

    @classmethod
    def generate_alerts(
        cls,
        tenant_id: str = "tenant_default",
        cases: Optional[List[Any]] = None,
        ingestion_jobs: Optional[List[Any]] = None,
        eval_runs: Optional[List[Any]] = None,
        traces: Optional[List[Any]] = None,
    ) -> List[OperationalAlert]:
        """
        Evaluate active data and return a list of actionable OperationalAlert objects.
        """
        alerts: List[OperationalAlert] = []
        cases_list = cases or []
        jobs_list = ingestion_jobs or []
        eval_list = eval_runs or []
        trace_list = traces or []

        # 1. High-Risk / Critical Cases Alert
        critical_cases = [c for c in cases_list if str(getattr(c, "risk_level", "")).upper() in {"CRITICAL", "HIGH"}]
        if critical_cases:
            alerts.append(
                OperationalAlert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                    title=f"High Risk Compliance Alert ({len(critical_cases)} Cases)",
                    description=f"{len(critical_cases)} case(s) in tenant '{tenant_id}' possess HIGH or CRITICAL risk levels.",
                    category=AlertCategoryEnum.HIGH_RISK_CASE,
                    severity=AlertSeverityEnum.CRITICAL if any(str(getattr(c, "risk_level", "")).upper() == "CRITICAL" for c in critical_cases) else AlertSeverityEnum.HIGH,
                    tenant_id=tenant_id,
                    resource_id=getattr(critical_cases[0], "case_id", None),
                    action_required="Assign Senior Tax Reviewer for priority investigation.",
                )
            )

        # 2. High Financial Exposure Alert (> INR 50,000)
        high_exp_cases = [c for c in cases_list if float(getattr(c, "financial_exposure", 0.0)) > 50000.0]
        if high_exp_cases:
            total_exp = sum(float(getattr(c, "financial_exposure", 0.0)) for c in high_exp_cases)
            alerts.append(
                OperationalAlert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                    title=f"High Financial Exposure Warning (INR {total_exp:,.2f})",
                    description=f"{len(high_exp_cases)} case(s) exceed financial exposure threshold of INR 50,000.",
                    category=AlertCategoryEnum.HIGH_FINANCIAL_EXPOSURE,
                    severity=AlertSeverityEnum.HIGH,
                    tenant_id=tenant_id,
                    resource_id=getattr(high_exp_cases[0], "case_id", None),
                    action_required="Audit tax rate mismatches and ITC claim eligibility before filing.",
                )
            )

        # 3. Failed Ingestion Job Alert
        failed_jobs = [j for j in jobs_list if str(getattr(j, "status", "")).upper() in {"FAILED", "REJECTED"}]
        if failed_jobs:
            alerts.append(
                OperationalAlert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                    title=f"Data Ingestion Failure Detected ({len(failed_jobs)} Jobs)",
                    description=f"{len(failed_jobs)} dataset ingestion job(s) failed or encountered severe parsing errors.",
                    category=AlertCategoryEnum.FAILED_INGESTION,
                    severity=AlertSeverityEnum.HIGH,
                    tenant_id=tenant_id,
                    resource_id=getattr(failed_jobs[0], "job_id", None),
                    action_required="Inspect rejected records log and verify raw CSV/JSON format.",
                )
            )

        # 4. Poor Data Quality Alert (< 75.0 quality score)
        degraded_jobs = [j for j in jobs_list if float(getattr(j, "quality_score", 100.0)) < 75.0]
        if degraded_jobs:
            alerts.append(
                OperationalAlert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                    title=f"Degraded Dataset Quality Alert",
                    description=f"Batch quality score ({getattr(degraded_jobs[0], 'quality_score', 0):.1f}/100) is below operational threshold (75.0).",
                    category=AlertCategoryEnum.POOR_DATA_QUALITY,
                    severity=AlertSeverityEnum.WARNING,
                    tenant_id=tenant_id,
                    resource_id=getattr(degraded_jobs[0], "job_id", None),
                    action_required="Review duplicate records and mandatory field completeness report.",
                )
            )

        # 5. Investigation Failure / Timeout Alert
        failed_traces = [t for t in trace_list if str(getattr(t, "status", "")).upper() in {"FAILED", "TIMEOUT"}]
        if failed_traces:
            alerts.append(
                OperationalAlert(
                    alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                    title=f"Investigation Step Failure / Timeout",
                    description=f"{len(failed_traces)} investigation step(s) failed or timed out during tool execution.",
                    category=AlertCategoryEnum.INVESTIGATION_FAILURE,
                    severity=AlertSeverityEnum.WARNING,
                    tenant_id=tenant_id,
                    resource_id=getattr(failed_traces[0], "investigation_id", None),
                    action_required="Inspect operational trace log for tool timeout or permission errors.",
                )
            )

        # 6. AI Evaluation Regression Alert
        if eval_list:
            latest_run = eval_list[-1]
            if float(getattr(latest_run, "overall_score", 100.0)) < 90.0:
                alerts.append(
                    OperationalAlert(
                        alert_id=f"ALT-{uuid.uuid4().hex[:8].upper()}",
                        title=f"AI Investigation Evaluation Regression Alert",
                        description=f"Latest evaluation run score ({getattr(latest_run, 'overall_score', 0):.1f}%) dropped below 90% benchmark.",
                        category=AlertCategoryEnum.EVALUATION_REGRESSION,
                        severity=AlertSeverityEnum.HIGH,
                        tenant_id=tenant_id,
                        resource_id=getattr(latest_run, "run_id", None),
                        action_required="Run golden dataset regression evaluation to locate failing test cases.",
                    )
                )

        logger.info(f"Evaluated {len(alerts)} operational alert(s) for tenant '{tenant_id}'.")
        return alerts
