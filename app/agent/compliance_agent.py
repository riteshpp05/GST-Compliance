"""
UC15 GST Compliance Agent — Main Orchestrator Agent (v2.0)
Source-Agnostic Engine: Coordinates Ingestion (Excel, CSV, JSON, Mock, SAP) -> Normalization
-> Repository -> Rule Engine 2.0 -> Decision Engine -> Results Persistence.
"""
from __future__ import annotations

import os
from typing import List, Optional, Union

from app.agent.output_writer import ResultsWriter
from app.agent.summary import LLMSummarizer
from app.config.settings import settings
from app.data.loaders.base import BaseInvoiceLoader
from app.data.loaders.csv_loader import CSVInvoiceLoader
from app.data.loaders.excel_loader import ExcelInvoiceLoader
from app.data.loaders.json_loader import JSONInvoiceLoader
from app.data.loaders.mock_loader import MockInvoiceLoader
from app.data.loaders.s4hana_odata_loader import S4HanaODataInvoiceLoader
from app.data.loaders.hybrid_loader import HybridInvoiceLoader
from app.data.repositories.invoice_repository import InMemoryInvoiceRepository
from app.domain.models.ingestion import IngestionBatchResult
from app.domain.models.risk import BatchRiskReport, RiskAssessment
from app.domain.models.validation import ComplianceDecision
from app.engine.decision_engine import DecisionEngine
from app.engine.risk_engine import RiskEngine
from app.engine.validation_engine import ValidationEngine
from app.infrastructure.logging import get_logger
from app.rules.context import ValidationContext
from app.rules.registry import create_default_registry
from app.historical.services.historical_service import HistoricalService
from app.historical.models.report import HistoricalReport
from app.historical.models.period import PeriodType
from app.financial.services.financial_service import FinancialService
from app.financial.models.report import FinancialReport
from app.intelligence.services.intelligence_service import IntelligenceService
from app.intelligence.reporting.report import IntelligenceReport
from app.investigation.investigation_service import InvestigationService
from app.investigation.models import InvestigationProfile


from app.db.connection import is_db_configured, init_db

logger = get_logger(__name__)


class GSTComplianceAgent:
    """
    Main compliance orchestration agent for UC15 (v2.0).
    Source-agnostic: accepts Excel, CSV, JSON, Mock, SAP OData, or custom BaseInvoiceLoader instances.
    """

    def __init__(
        self,
        use_llm: bool = False,
        excel_path: Optional[str] = None,
        source_file: Optional[str] = None,
        source_type: Optional[str] = None,
        loader: Optional[BaseInvoiceLoader] = None,
        mock: bool = False,
        sap: bool = False,
        hybrid: bool = False,
    ):
        self.use_llm = use_llm
        self.writer = ResultsWriter()
        self.summarizer = LLMSummarizer() if use_llm else None
        self.repository = InMemoryInvoiceRepository()
        self.registry = create_default_registry()
        self.decision_engine = DecisionEngine()
        self.risk_engine = RiskEngine()
        self.historical_service = HistoricalService()
        self.financial_service = FinancialService()
        self.intelligence_service = IntelligenceService()
        self.investigation_service = InvestigationService()
        self.validation_engine: Optional[ValidationEngine] = None
        self.ingestion_result: Optional[IngestionBatchResult] = None
        self.batch_risk_report: Optional[BatchRiskReport] = None
        self._initialized = False

        auth_tuple = (settings.sap_username, settings.sap_password) if settings.sap_username and settings.sap_password else None
        sap_loader_inst = S4HanaODataInvoiceLoader(
            base_url=settings.sap_odata_base_url,
            auth=auth_tuple,
            company_code=settings.sap_company_code,
            sap_client=settings.sap_client,
            outward_service=settings.sap_outward_service,
            outward_entity=settings.sap_outward_entity,
            inward_service=settings.sap_inward_service,
            inward_entity=settings.sap_inward_entity,
            mock_fallback=True,
        )

        # Select appropriate loader adapter
        if loader is not None:
            self.loader: BaseInvoiceLoader = loader
        elif mock:
            self.loader = MockInvoiceLoader()
        elif hybrid or source_type == "hybrid":
            self.loader = HybridInvoiceLoader(sap_loader=sap_loader_inst, statutory_file=source_file)
        elif sap or source_type == "sap_s4hana_odata":
            self.loader = sap_loader_inst
        else:
            file_target = source_file or excel_path or settings.excel_file
            ext = os.path.splitext(file_target)[1].lower()
            if ext == ".csv":
                self.loader = CSVInvoiceLoader(file_target)
            elif ext == ".json":
                self.loader = JSONInvoiceLoader(file_target)
            else:
                self.loader = ExcelInvoiceLoader(excel_path=file_target)

    def _initialize(self) -> None:
        if self._initialized:
            return
        logger.info(f"Initializing GST Compliance Agent with loader: {type(self.loader).__name__}...")

        if is_db_configured():
            try:
                init_db()
                logger.info("Database schema auto-initialized for relational persistence backend.")
            except Exception as e:
                logger.warning(f"Database auto-initialization exception: {e}")

        # Execute unified ingestion
        self.ingestion_result = self.loader.load()
        invoices = self.ingestion_result.valid_invoices
        logger.info(
            f"Ingestion completed: {self.ingestion_result.valid_count} valid, "
            f"{self.ingestion_result.warning_count} warnings, "
            f"{self.ingestion_result.invalid_count} rejected."
        )

        hsn_master = self.loader.load_hsn_master()
        state_codes = self.loader.load_state_codes()

        # If HSN master or State codes are empty (e.g. from CSV/JSON), fallback to default Excel reference
        if not hsn_master or not state_codes:
            if os.path.exists(settings.excel_file):
                try:
                    ref_loader = ExcelInvoiceLoader(excel_path=settings.excel_file)
                    if not hsn_master:
                        hsn_master = ref_loader.load_hsn_master()
                    if not state_codes:
                        state_codes = ref_loader.load_state_codes()
                except Exception as e:
                    logger.warning(f"Could not load fallback master references from Excel: {e}")

        if hasattr(self.repository, "clear") and callable(getattr(self.repository, "clear")):
            self.repository.clear()
        self.repository.add_batch(invoices)
        self.repository.set_hsn_master(hsn_master)
        self.repository.set_state_codes(state_codes)

        context = ValidationContext(
            hsn_master=hsn_master,
            state_ref=state_codes,
            eway_bill_threshold=settings.eway_bill_threshold_inr,
            rate_tolerance_pct=settings.rate_tolerance_pct,
            itc_blocked_keywords=settings.itc_blocked_keywords,
        )

        self.validation_engine = ValidationEngine(
            registry_or_rules=self.registry,
            context=context,
        )
        self._initialized = True

    def run_all(self) -> List[ComplianceDecision]:
        """Validate all ingested invoices, compute risk assessments, and persist results."""
        self._initialize()
        invoices = self.repository.list_all()
        logger.info(f"Running compliance validation and risk assessment for {len(invoices)} invoices...")

        reports = []
        decisions: List[ComplianceDecision] = []
        for inv in invoices:
            report = self.validation_engine.validate(inv)
            decision = self.decision_engine.decide(inv, report)
            reports.append(report)
            decisions.append(decision)

        # Batch risk evaluation
        self.batch_risk_report = self.risk_engine.assess_batch(
            invoices=invoices,
            validation_reports=reports,
            compliance_decisions=decisions,
            context=self.validation_engine.context,
        )

        self.writer.write_results(decisions)
        self._print_summary(decisions)

        # Batch historical recording
        try:
            self.historical_service.record_batch(decisions, invoices=invoices)
        except Exception as e:
            logger.warning(f"Failed to record batch into historical intelligence service: {e}")

        # Batch financial evaluation
        try:
            self.financial_service.evaluate_batch(decisions, invoices=invoices)
        except Exception as e:
            logger.warning(f"Failed to record batch into financial impact service: {e}")

        # Batch duplicate & anomaly intelligence evaluation
        try:
            self.intelligence_service.evaluate_batch(invoices=invoices, decisions=decisions)
        except Exception as e:
            logger.warning(f"Failed to evaluate batch in intelligence service: {e}")

        # Batch root cause & blast radius investigation evaluation
        try:
            intel_report = self.intelligence_service.get_report()
            fin_impacts = self.financial_service.list_all_impacts()
            self.investigation_service.evaluate_batch(
                invoices=invoices,
                decisions=decisions,
                financial_impacts=fin_impacts,
                duplicate_candidates=intel_report.duplicate_candidates if intel_report else None,
                duplicate_clusters=intel_report.duplicate_clusters if intel_report else None,
                anomaly_findings=intel_report.anomaly_findings if intel_report else None,
            )
        except Exception as e:
            logger.warning(f"Failed to evaluate batch in investigation service: {e}")

        return decisions

    def run_all_with_investigation(self) -> tuple[List[ComplianceDecision], Optional[InvestigationProfile]]:
        """Run validation, risk evaluation, and return both decisions and investigation profile."""
        decisions = self.run_all()
        profile = self.investigation_service.get_investigation_profile()
        return decisions, profile

    def get_investigation_profile(self, investigation_id: Optional[str] = None) -> Optional[InvestigationProfile]:
        """Generate investigation profile from currently evaluated decisions."""
        return self.investigation_service.get_investigation_profile(investigation_id)

    def run_all_with_history(self, period_type: PeriodType = PeriodType.MONTHLY) -> tuple[List[ComplianceDecision], HistoricalReport]:
        """Run validation, risk evaluation, and return both decisions and historical time-series report."""
        decisions = self.run_all()
        report = self.historical_service.generate_report(period_type=period_type)
        return decisions, report

    def get_historical_report(self, period_type: PeriodType = PeriodType.MONTHLY) -> HistoricalReport:
        """Generate historical intelligence report from currently ingested records."""
        return self.historical_service.generate_report(period_type=period_type)

    def run_all_with_financial(self, top_n: int = 5) -> tuple[List[ComplianceDecision], FinancialReport]:
        """Run validation, risk evaluation, and return both decisions and financial impact report."""
        decisions = self.run_all()
        report = self.financial_service.generate_report(top_n=top_n)
        return decisions, report

    def get_financial_report(self, top_n: int = 5) -> FinancialReport:
        """Generate financial exposure report from currently evaluated decisions."""
        return self.financial_service.generate_report(top_n=top_n)

    def run_all_with_intelligence(self) -> tuple[List[ComplianceDecision], IntelligenceReport]:
        """Run validation, risk evaluation, and return both decisions and duplicate/anomaly intelligence report."""
        decisions = self.run_all()
        report = self.intelligence_service.get_report()
        return decisions, report

    def get_intelligence_report(self) -> IntelligenceReport:
        """Generate duplicate and anomaly intelligence report from evaluated decisions."""
        return self.intelligence_service.get_report()

    def run_all_with_risk(self) -> BatchRiskReport:
        """Run all invoices and return the full BatchRiskReport."""
        self.run_all()
        return self.batch_risk_report

    def run_invoice(self, invoice_no: str) -> Optional[ComplianceDecision]:
        """Run validation and risk assessment for a single specific invoice number."""
        self._initialize()
        invoice = self.repository.get_by_id(invoice_no)
        if invoice is None:
            logger.warning(f"Invoice {invoice_no} not found.")
            print(f"[Agent] Invoice {invoice_no} not found.")
            return None

        report = self.validation_engine.validate(invoice)
        decision = self.decision_engine.decide(invoice, report)

        # Evaluate risk for single invoice
        self.risk_engine.assess(
            invoice=invoice,
            validation_report=report,
            compliance_decision=decision,
            context=self.validation_engine.context,
        )

        # Evaluate financial impact for single invoice
        try:
            self.financial_service.evaluate_decision(decision, invoice)
        except Exception as e:
            logger.warning(f"Failed to evaluate financial impact for invoice {invoice_no}: {e}")

        self.writer.write_results([decision])
        self._print_single(decision, verbose=True)
        return decision

    def _print_single(self, d: ComplianceDecision, verbose: bool = False) -> None:
        print(f"\n{d.invoice_no}  {d.counterparty_name}  ({d.direction})")
        print(f"  {d.failed_gate_count} gate(s) failed  ->  {d.status}")
        if getattr(d, "risk_score", None) is not None:
            print(f"  Risk Profile: {getattr(d, 'risk_level', 'LOW')} | Score: {d.risk_score}/100 | Priority: {getattr(d, 'priority', 'P4')}")
        impact = self.financial_service.get_impact_by_invoice_id(d.invoice_no)
        if impact and impact.potential_exposure is not None and impact.potential_exposure > 0:
            print(f"  Potential Exposure: INR {impact.potential_exposure:,.2f} ({impact.impact_type.value}, {impact.direction.value})")
        if verbose:
            for g in d.gates:
                print(f"    Gate {g.gate_no} [{g.status:14}] {g.name}: {g.detail}")
            if getattr(d, "risk_assessment", None) is not None and d.risk_assessment.risk_factors:
                print(f"  Risk Drivers:")
                for f in d.risk_assessment.risk_factors[:4]:
                    print(f"    - {f.name}: +{f.contribution:.1f} ({f.category})")
            print(f"  Justification: {d.justification}")
            print(f"  SAP action: {d.sap_action}")
            print(f"  Audit ref: {d.audit_trail_ref}")
            if d.alerts:
                print(f"  Alerts: {', '.join(d.alerts)}")

    def _print_summary(self, results: List[ComplianceDecision]) -> None:
        summary = LLMSummarizer._fallback_summary(results)
        print("\n" + "=" * 60)
        print("  UC15 GST Compliance Validation Agent — Run Summary")
        print("=" * 60)
        print(summary)
        if self.batch_risk_report is not None:
            dist = self.batch_risk_report.distribution
            print("\n  Risk Distribution (Risk Engine 1.0):")
            print(f"    Average Risk Score : {dist.average_risk_score}/100")
            print(f"    Risk Levels        : {dist.by_level}")
            print(f"    Priorities         : {dist.by_priority}")
            print(f"    Top Categories     : {dict(sorted(dist.by_category.items(), key=lambda x: x[1], reverse=True)[:5])}")
        agg_exp = self.financial_service.get_aggregate_exposure()
        if agg_exp and agg_exp.total_potential_exposure > 0:
            print(f"\n  Financial Exposure (Financial Engine):")
            print(f"    Total Exposure     : INR {agg_exp.total_potential_exposure:,.2f}")
            print(f"    Invoices Evaluated : {agg_exp.total_invoices_analyzed} ({agg_exp.calculated_count} calculated, {agg_exp.undetermined_count} undetermined)")
            if agg_exp.total_tax_difference > 0:
                print(f"    Tax Rate Mismatch  : INR {agg_exp.total_tax_difference:,.2f}")
            if agg_exp.total_itc_exposure > 0:
                print(f"    ITC at Risk        : INR {agg_exp.total_itc_exposure:,.2f}")
        print("=" * 60)

