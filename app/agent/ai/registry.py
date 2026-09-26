"""
app.agent.ai.registry
=====================
Controlled Tool Registry for UC15 AI Investigation Agent (Sprint 12.1 + Sprint 16 Security Upgrade).
Exposes existing S1–S11 deterministic engines as strictly typed, permission-aware, reliable tools.
Prevents arbitrary tool execution or unauthorized data mutation.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, Field

from app.agent.ai.models import ToolResult
from app.infrastructure.logging import get_logger
from app.security.auth import AuthenticatedPrincipal, get_internal_compatibility_principal
from app.security.authorization import PermissionEvaluator
from app.security.exceptions import ToolPermissionDeniedException
from app.security.rbac import PermissionEnum

logger = get_logger(__name__)


class ToolDefinition(BaseModel):
    """
    Metadata specification for a tool exposed to the AI agent.
    Enforces strict read-only classification and required RBAC permissions.
    """
    name: str = Field(..., description="Unique tool name.")
    description: str = Field(..., description="Clear explanation of tool utility.")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for tool input arguments.")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for tool output structure.")
    handler: Callable[..., Any] = Field(..., description="Executable Python handler function.")
    category: str = Field("INVESTIGATION", description="Tool category classification.")
    side_effect_type: str = Field("READ_ONLY", description="READ_ONLY, ANALYTICAL, or HUMAN_CONTROLLED.")
    required_permissions: List[PermissionEnum] = Field(
        default_factory=lambda: [PermissionEnum.TOOL_EXECUTE],
        description="RBAC permissions required to invoke this tool.",
    )
    timeout_seconds: float = Field(20.0, ge=0.1, le=120.0, description="Execution timeout limit.")
    max_retries: int = Field(2, ge=0, le=5, description="Safe retry attempts.")
    is_idempotent: bool = Field(True, description="Whether re-execution is safe and idempotent.")
    read_only_flag: Optional[bool] = Field(None, alias="read_only", description="Optional explicit read_only flag.")

    def model_post_init(self, __context: Any) -> None:
        if self.read_only_flag is False:
            self.side_effect_type = "MUTATING"

    @property
    def read_only(self) -> bool:
        """Enforce strict read-only constraint for AI investigation tools."""
        if self.read_only_flag is not None:
            return self.read_only_flag
        return self.side_effect_type in {"READ_ONLY", "ANALYTICAL"}


class ToolRegistry:
    """
    Centralized registry managing approved tools available to the AI Investigation Agent.
    Enforces permission-awareness, schema validation, and read-only boundaries in Sprint 16.
    """

    def __init__(self, agent: Optional[Any] = None) -> None:
        if agent is None:
            from app.agent.compliance_agent import GSTComplianceAgent
            self.agent = GSTComplianceAgent()
        else:
            self.agent = agent
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        if tool.side_effect_type == "HUMAN_CONTROLLED" or not tool.read_only:
            # Strictly enforce read-only execution for AI investigation tools
            if not tool.read_only:
                raise ValueError(f"Tool '{tool.name}' cannot be registered: non read-only tools strictly blocked for AI.")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool '{tool.name}' ({tool.category}, side_effect={tool.side_effect_type})")

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def execute(self, name: str, principal: Optional[AuthenticatedPrincipal] = None, **kwargs: Any) -> ToolResult:
        """
        Execute a registered tool safely with permission evaluation, argument extraction,
        and capture structured ToolResult.
        """
        tool = self.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                success=False,
                errors=[f"Tool '{name}' is not registered in the tool registry."],
            )

        eff_principal = principal or get_internal_compatibility_principal()

        # Permission Check
        for req_perm in tool.required_permissions:
            if not PermissionEvaluator.has_permission(eff_principal, req_perm):
                logger.warning(f"Permission denied for principal '{eff_principal.principal_id}' on tool '{name}'")
                return ToolResult(
                    tool_name=name,
                    success=False,
                    errors=[f"Permission denied for principal '{eff_principal.principal_id}' to execute tool '{name}'."],
                )

        if not tool.read_only:
            return ToolResult(
                tool_name=name,
                success=False,
                errors=[f"Tool '{name}' violates safety policy: non read-only tool execution blocked."],
            )

        start_time = time.perf_counter()
        try:
            res = tool.handler(**kwargs)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

            # Serialize Pydantic/dataclass models if present
            structured_data = {}
            evidence = {}
            if hasattr(res, "to_dict") and callable(res.to_dict):
                structured_data = res.to_dict()
            elif hasattr(res, "model_dump") and callable(res.model_dump):
                structured_data = res.model_dump()
            elif isinstance(res, dict):
                structured_data = res
            elif isinstance(res, list):
                structured_data = {"items": [item.to_dict() if hasattr(item, "to_dict") else str(item) for item in res]}
            else:
                structured_data = {"result": str(res)}

            if isinstance(structured_data, dict) and "evidence" in structured_data:
                evidence = structured_data["evidence"]

            return ToolResult(
                tool_name=name,
                success=True,
                structured_data=structured_data,
                evidence=evidence if isinstance(evidence, dict) else {"raw": str(evidence)},
                execution_time_ms=elapsed_ms,
                metadata={"category": tool.category, "read_only": True, "side_effect_type": tool.side_effect_type},
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            logger.error(f"Execution error in tool '{name}': {e}")
            return ToolResult(
                tool_name=name,
                success=False,
                errors=[f"Tool '{name}' execution failed: {str(e)}"],
                execution_time_ms=elapsed_ms,
            )

    def _register_default_tools(self) -> None:
        """Register the 10 standard read-only tools wrapping S1-S11 deterministic & RAG services."""

        # 1. validate_invoice
        def _h_validate_invoice(invoice_no: Optional[str] = None, invoice_id: Optional[str] = None, **kwargs) -> Any:
            inv = invoice_no or invoice_id or kwargs.get("invoice_no") or kwargs.get("invoice_id") or ""
            return self.agent.run_invoice(inv)

        self.register(
            ToolDefinition(
                name="validate_invoice",
                description="Run 6-gate compliance validation and risk assessment for a specific invoice number.",
                input_schema={"type": "object", "properties": {"invoice_no": {"type": "string"}}, "required": ["invoice_no"]},
                output_schema={"type": "object", "properties": {"status": {"type": "string"}, "gates": {"type": "array"}}},
                handler=_h_validate_invoice,
                category="COMPLIANCE",
                side_effect_type="ANALYTICAL",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=15.0,
            )
        )

        # 2. get_compliance_result
        def _h_get_compliance_result(invoice_no: Optional[str] = None, invoice_id: Optional[str] = None, **kwargs) -> Any:
            inv = invoice_no or invoice_id or kwargs.get("invoice_no") or kwargs.get("invoice_id")
            if inv:
                d = self.agent.run_invoice(inv)
                return d.to_dict() if d else {"error": f"Invoice {inv} not found"}
            results = self.agent.run_all()
            return [r.to_dict() for r in results]

        self.register(
            ToolDefinition(
                name="get_compliance_result",
                description="Retrieve statutory compliance decision and 6 gate results for an invoice or full batch.",
                input_schema={"type": "object", "properties": {"invoice_no": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_get_compliance_result,
                category="COMPLIANCE",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 3. get_risk_assessment
        def _h_get_risk_assessment(invoice_no: Optional[str] = None, invoice_id: Optional[str] = None, **kwargs) -> Any:
            inv = invoice_no or invoice_id or kwargs.get("invoice_no") or kwargs.get("invoice_id")
            if inv:
                d = self.agent.run_invoice(inv)
                if d and getattr(d, "risk_assessment", None):
                    return d.risk_assessment.to_dict()
                return {"error": f"Risk assessment not found for {inv}"}
            report = self.agent.run_all_with_risk()
            return report.to_dict() if report else {}

        self.register(
            ToolDefinition(
                name="get_risk_assessment",
                description="Retrieve S3 risk score (0-100), risk level (LOW-CRITICAL), priority (P1-P4), and risk drivers.",
                input_schema={"type": "object", "properties": {"invoice_no": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_get_risk_assessment,
                category="RISK",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 4. get_financial_exposure
        def _h_get_financial_exposure(invoice_no: Optional[str] = None, invoice_id: Optional[str] = None, top_n: int = 5, **kwargs) -> Any:
            inv = invoice_no or invoice_id or kwargs.get("invoice_no") or kwargs.get("invoice_id")
            self.agent.run_all()
            if inv:
                imp = self.agent.financial_service.get_impact_by_invoice_id(inv)
                return imp.to_dict() if imp else {"error": f"No financial impact for {inv}"}
            rep = self.agent.financial_service.generate_report(top_n=top_n)
            return rep.to_dict()

        self.register(
            ToolDefinition(
                name="get_financial_exposure",
                description="Retrieve S6 financial exposure math (tax rate difference, blocked ITC exposure) without double counting.",
                input_schema={"type": "object", "properties": {"invoice_no": {"type": "string"}, "top_n": {"type": "integer"}}},
                output_schema={"type": "object"},
                handler=_h_get_financial_exposure,
                category="FINANCIAL",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 5. get_historical_patterns
        def _h_get_historical_patterns(period_type: str = "MONTHLY", **kwargs) -> Any:
            self.agent.run_all()
            rep = self.agent.historical_service.generate_report()
            return rep.to_dict()

        self.register(
            ToolDefinition(
                name="get_historical_patterns",
                description="Retrieve S5 historical compliance trends, counterparty profiles, and recurring rule failure patterns.",
                input_schema={"type": "object", "properties": {"period_type": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_get_historical_patterns,
                category="HISTORICAL",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 6. find_duplicates
        def _h_find_duplicates(invoice_no: Optional[str] = None, invoice_id: Optional[str] = None, **kwargs) -> Any:
            inv = invoice_no or invoice_id or kwargs.get("invoice_no") or kwargs.get("invoice_id")
            self.agent.run_all()
            rep = self.agent.intelligence_service.get_report()
            if not rep:
                return {"duplicate_candidates": [], "duplicate_clusters": []}
            cands = rep.duplicate_candidates
            if inv:
                cands = [c for c in cands if c.source_invoice_id == inv or c.matched_invoice_id == inv]
            return {
                "duplicate_candidates": [c.to_dict() for c in cands],
                "duplicate_clusters": [cl.to_dict() for cl in rep.duplicate_clusters],
            }

        self.register(
            ToolDefinition(
                name="find_duplicates",
                description="Retrieve S7 exact SHA-256 and near Levenshtein duplicate candidate matches and transitive clusters.",
                input_schema={"type": "object", "properties": {"invoice_no": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_find_duplicates,
                category="INTELLIGENCE",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 7. find_anomalies
        def _h_find_anomalies(invoice_no: Optional[str] = None, invoice_id: Optional[str] = None, **kwargs) -> Any:
            inv = invoice_no or invoice_id or kwargs.get("invoice_no") or kwargs.get("invoice_id")
            self.agent.run_all()
            rep = self.agent.intelligence_service.get_report()
            if not rep:
                return {"anomaly_findings": []}
            findings = rep.anomaly_findings
            if inv:
                findings = [f for f in findings if f.invoice_id == inv]
            return {"anomaly_findings": [f.to_dict() for f in findings]}

        self.register(
            ToolDefinition(
                name="find_anomalies",
                description="Retrieve S7 statistical transaction anomaly findings (value, tax rate, frequency outliers via Robust Z-Score).",
                input_schema={"type": "object", "properties": {"invoice_no": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_find_anomalies,
                category="INTELLIGENCE",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 8. investigate_root_cause
        def _h_investigate_root_cause(root_cause_id: Optional[str] = None, **kwargs) -> Any:
            self.agent.run_all()
            prof = self.agent.get_investigation_profile()
            if not prof:
                return {"root_cause_candidates": []}
            if root_cause_id:
                for c in prof.root_cause_candidates:
                    if c.root_cause_id == root_cause_id:
                        return c.to_dict()
                return {"error": f"Root cause {root_cause_id} not found"}
            return {"root_cause_candidates": [c.to_dict() for c in prof.root_cause_candidates]}

        self.register(
            ToolDefinition(
                name="investigate_root_cause",
                description="Retrieve S8 root cause hypothesis candidates, confidence ratings, evidence scoring, and likelihood.",
                input_schema={"type": "object", "properties": {"root_cause_id": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_investigate_root_cause,
                category="INVESTIGATION",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 9. get_blast_radius
        def _h_get_blast_radius(blast_radius_id: Optional[str] = None, **kwargs) -> Any:
            self.agent.run_all()
            prof = self.agent.get_investigation_profile()
            if not prof or not prof.blast_radius:
                return {"error": "Blast radius unavailable"}
            return prof.blast_radius.to_dict()

        self.register(
            ToolDefinition(
                name="get_blast_radius",
                description="Retrieve S9 multi-dimensional blast radius scope (affected invoices, counterparties, rules, exposure, systemic classification).",
                input_schema={"type": "object", "properties": {"blast_radius_id": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_get_blast_radius,
                category="INVESTIGATION",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=20.0,
            )
        )

        # 10. retrieve_gst_knowledge
        def _h_retrieve_gst_knowledge(
            query: str = "",
            user_query: str = "",
            topic: Optional[str] = None,
            transaction_date: Optional[str] = None,
            jurisdiction: Optional[str] = None,
            document_type: Optional[str] = None,
            top_k: int = 3,
            **kwargs,
        ) -> Any:
            q = (query or user_query or "GST statutory compliance rules").strip()
            from app.knowledge import KnowledgeService, RetrievalQuery
            ks = getattr(self.agent, "knowledge_service", None)
            if not ks:
                ks = KnowledgeService()
                setattr(self.agent, "knowledge_service", ks)

            ret_query = RetrievalQuery(
                query=q,
                topic=topic,
                transaction_date=transaction_date,
                jurisdiction=jurisdiction,
                top_k=top_k,
            )
            res = ks.retrieve(ret_query)
            return res.model_dump()

        self.register(
            ToolDefinition(
                name="retrieve_gst_knowledge",
                description="Retrieve evidence-grounded statutory GST rules, notifications, circulars, and policy context.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "topic": {"type": "string"},
                        "transaction_date": {"type": "string"},
                        "jurisdiction": {"type": "string"},
                        "document_type": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                },
                handler=_h_retrieve_gst_knowledge,
                category="KNOWLEDGE",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.KNOWLEDGE_RETRIEVE, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=15.0,
            )
        )

        # 11. inspect_ingestion (Sprint 17)
        def _h_inspect_ingestion(ingestion_id: str = "", **kwargs) -> Any:
            from app.data.service import get_data_ingestion_service
            ds = get_data_ingestion_service()
            job = ds.get_ingestion_job(ingestion_id)
            if not job:
                return {"error": f"IngestionJob '{ingestion_id}' not found."}
            return job

        self.register(
            ToolDefinition(
                name="inspect_ingestion",
                description="Inspect details, status, and record counts of an ingestion job.",
                input_schema={"type": "object", "properties": {"ingestion_id": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_inspect_ingestion,
                category="DATA",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.DATA_READ, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=10.0,
            )
        )

        # 12. get_data_quality (Sprint 17)
        def _h_get_data_quality(ingestion_id: str = "", **kwargs) -> Any:
            from app.data.service import get_data_ingestion_service
            ds = get_data_ingestion_service()
            report = ds.get_data_quality_report(ingestion_id)
            if not report:
                return {"error": f"DataQualityReport for '{ingestion_id}' not found."}
            return report.to_dict()

        self.register(
            ToolDefinition(
                name="get_data_quality",
                description="Retrieve aggregated 6-dimension data quality score and dimension breakdown.",
                input_schema={"type": "object", "properties": {"ingestion_id": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_get_data_quality,
                category="DATA",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.DATA_READ, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=10.0,
            )
        )

        # 13. get_rejected_records (Sprint 17)
        def _h_get_rejected_records(ingestion_id: str = "", **kwargs) -> Any:
            from app.data.service import get_data_ingestion_service
            ds = get_data_ingestion_service()
            recs = ds.get_rejected_records(ingestion_id)
            return [r.to_dict() for r in recs]

        self.register(
            ToolDefinition(
                name="get_rejected_records",
                description="Retrieve rejected or duplicate records with structural/validation error details.",
                input_schema={"type": "object", "properties": {"ingestion_id": {"type": "string"}}},
                output_schema={"type": "array"},
                handler=_h_get_rejected_records,
                category="DATA",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.DATA_READ, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=10.0,
            )
        )

        # 14. get_record_lineage (Sprint 17)
        def _h_get_record_lineage(canonical_record_id: str = "", **kwargs) -> Any:
            from app.data.service import get_data_ingestion_service
            ds = get_data_ingestion_service()
            lin = ds.get_record_lineage(canonical_record_id)
            if not lin:
                return {"error": f"Lineage for canonical record '{canonical_record_id}' not found."}
            return lin.to_dict()

        self.register(
            ToolDefinition(
                name="get_record_lineage",
                description="Retrieve source-to-case data lineage and transformation provenance.",
                input_schema={"type": "object", "properties": {"canonical_record_id": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_get_record_lineage,
                category="DATA",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.DATA_READ, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=10.0,
            )
        )

        # --- Sprint 18 Tools ---

        # 15. create_investigation_plan (Sprint 18)
        def _h_create_investigation_plan(case_id: str = "", objective: str = "Investigate GST compliance", invoice_id: str = "", **kwargs) -> Any:
            from app.investigation.orchestrator import get_enterprise_orchestrator
            orch = get_enterprise_orchestrator()
            plan = orch.create_plan(case_id=case_id, objective=objective, invoice_id=invoice_id)
            return plan.to_dict()

        self.register(
            ToolDefinition(
                name="create_investigation_plan",
                description="Create a dependency-aware investigation plan with budget limits.",
                input_schema={"type": "object", "properties": {"case_id": {"type": "string"}, "objective": {"type": "string"}, "invoice_id": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_create_investigation_plan,
                category="INVESTIGATION",
                side_effect_type="ANALYTICAL",
                required_permissions=[PermissionEnum.INVESTIGATION_START, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=15.0,
            )
        )

        # 16. get_investigation_trace (Sprint 18)
        def _h_get_investigation_trace(investigation_id: str = "", **kwargs) -> Any:
            from app.investigation.trace import InvestigationTraceTracker
            trace = InvestigationTraceTracker.get_trace(investigation_id)
            return [t.model_dump() for t in trace]

        self.register(
            ToolDefinition(
                name="get_investigation_trace",
                description="Retrieve operational trace events for an investigation.",
                input_schema={"type": "object", "properties": {"investigation_id": {"type": "string"}}},
                output_schema={"type": "array"},
                handler=_h_get_investigation_trace,
                category="INVESTIGATION",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.CASE_READ, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=10.0,
            )
        )

        # 17. get_finding_explanation (Sprint 18)
        def _h_get_finding_explanation(case_id: str = "", finding_id: str = "", **kwargs) -> Any:
            from app.case.service import get_case_service
            from app.investigation.explainability import InvestigationExplainer
            case_svc = get_case_service()
            findings = case_svc.get_findings(case_id)
            target = next((f for f in findings if f.finding_id == finding_id), findings[0] if findings else None)
            if not target:
                return {"error": f"Finding '{finding_id}' not found."}
            ev_records = case_svc.get_evidence_records(case_id)
            explainer = InvestigationExplainer()
            exp = explainer.explain_finding(target, ev_records)
            return exp.model_dump()

        self.register(
            ToolDefinition(
                name="get_finding_explanation",
                description="Retrieve structured explanation separating FACT, INFERENCE, and RECOMMENDATION.",
                input_schema={"type": "object", "properties": {"case_id": {"type": "string"}, "finding_id": {"type": "string"}}},
                output_schema={"type": "object"},
                handler=_h_get_finding_explanation,
                category="EXPLAINABILITY",
                side_effect_type="READ_ONLY",
                required_permissions=[PermissionEnum.CASE_READ, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=10.0,
            )
        )

        # 18. run_investigation_evaluation (Sprint 18)
        def _h_run_investigation_evaluation(**kwargs) -> Any:
            from app.evaluation.framework import get_evaluation_framework
            fw = get_evaluation_framework()
            run = fw.run_evaluation()
            return run.to_dict()

        self.register(
            ToolDefinition(
                name="run_investigation_evaluation",
                description="Run AI investigation evaluation framework across golden dataset.",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                handler=_h_run_investigation_evaluation,
                category="EVALUATION",
                side_effect_type="ANALYTICAL",
                required_permissions=[PermissionEnum.CASE_READ, PermissionEnum.TOOL_EXECUTE],
                timeout_seconds=60.0,
            )
        )


_GLOBAL_TOOL_REGISTRY: Optional[ToolRegistry] = None


def get_global_tool_registry() -> ToolRegistry:
    """Singleton getter for global ToolRegistry."""
    global _GLOBAL_TOOL_REGISTRY
    if _GLOBAL_TOOL_REGISTRY is None:
        _GLOBAL_TOOL_REGISTRY = ToolRegistry()
    return _GLOBAL_TOOL_REGISTRY
